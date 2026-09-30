//! One Monte Carlo projection, matching `Projection` in `code/inv_proj.py`.
//!
//! The packed input (little-endian) is:
//! `b"FPR1"`, `u32` asset count, `u32` years, `u32` projections in this call,
//! `u32` index of the first projection (0-based, so seeds stay aligned),
//! `u64` master seed,
//! `f64` initial capital, `f64` cash buffer, `u32` liquidity / shortfall / replenishment
//! indexes, `u32` mix count, then mix pairs (`u32` index, `f64` weight),
//! then for each asset `u32` segment count and segments (`u32` from_year, `f64` mu, `f64` sigma),
//! then `u32` correlation count and triples (`u32` i, `u32` j, `f64` rho),
//! then `u32` flow mode (`0` = one shared vector of `years` f64s,
//! `1` = `projections * years` f64s, projection by projection).
//!
//! An optional trailer asks the engine to also write `output.csv` and
//! `audit.txt`: `u32` name count, then each display name as `u32` byte
//! length plus UTF-8, then `u32` append (`0` creates the files and writes
//! the header, `1` appends rows), then the CSV path and the audit path.
//! A length of zero skips that file.

use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};

use crate::py_random::PyRandom;

const STREAM_RETURNS: u64 = 1;
const MAX_CELLS: usize = 50_000_000;

pub fn mix_seed(master: u64, stream: u64, projection_id: u64) -> u64 {
    let mut x = master.wrapping_add(0x9E3779B97F4A7C15);
    x ^= stream.wrapping_mul(0xBF58476D1CE4E5B9);
    x ^= projection_id.wrapping_mul(0x94D049BB133111EB);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D049BB133111EB);
    x ^ (x >> 31)
}

struct Spec {
    n_assets: usize,
    n_years: usize,
    n_projections: usize,
    /// 0-based index of the first projection in this call.
    start_projection: usize,
    rng_seed: u64,
    initial_capital: f64,
    cash_buffer: f64,
    liquidity: usize,
    shortfall: usize,
    replenishment: usize,
    mix: Vec<(usize, f64)>,
    mu: Vec<Vec<f64>>,
    sigma: Vec<Vec<f64>>,
    cholesky: Vec<Vec<f64>>,
    /// `None` means one shared schedule lives in `flows`.
    per_projection_flows: bool,
    flows: Vec<f64>,
    names: Vec<String>,
    csv_path: Option<String>,
    audit_path: Option<String>,
    append_outputs: bool,
}

struct Reader<'a> {
    data: &'a [u8],
    at: usize,
}

impl<'a> Reader<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, at: 0 }
    }

    fn take(&mut self, n: usize) -> Result<&'a [u8], String> {
        let end = self
            .at
            .checked_add(n)
            .ok_or_else(|| "truncated spec".to_string())?;
        if end > self.data.len() {
            return Err("truncated spec".to_string());
        }
        let slice = &self.data[self.at..end];
        self.at = end;
        Ok(slice)
    }

    fn u32(&mut self) -> Result<u32, String> {
        let bytes: [u8; 4] = self
            .take(4)?
            .try_into()
            .map_err(|_| "truncated spec".to_string())?;
        Ok(u32::from_le_bytes(bytes))
    }

    fn u64(&mut self) -> Result<u64, String> {
        let bytes: [u8; 8] = self
            .take(8)?
            .try_into()
            .map_err(|_| "truncated spec".to_string())?;
        Ok(u64::from_le_bytes(bytes))
    }

    fn f64(&mut self) -> Result<f64, String> {
        let bytes: [u8; 8] = self
            .take(8)?
            .try_into()
            .map_err(|_| "truncated spec".to_string())?;
        Ok(f64::from_le_bytes(bytes))
    }

    fn string(&mut self) -> Result<String, String> {
        let len = self.u32()? as usize;
        if len > 1_048_576 {
            return Err("string in spec is too long".to_string());
        }
        let bytes = self.take(len)?.to_vec();
        String::from_utf8(bytes).map_err(|_| "spec string is not utf-8".to_string())
    }
}

fn checked_index(index: u32, n: usize, label: &str) -> Result<usize, String> {
    let index = index as usize;
    if index >= n {
        return Err(format!("{label} index {index} is outside 0..{n}"));
    }
    Ok(index)
}

fn cholesky(matrix: &[Vec<f64>]) -> Result<Vec<Vec<f64>>, String> {
    let n = matrix.len();
    let mut lower = vec![vec![0.0; n]; n];
    for i in 0..n {
        for j in 0..=i {
            let mut scale = 0.0;
            for k in 0..j {
                scale += lower[i][k] * lower[j][k];
            }
            if i == j {
                let value = matrix[i][i] - scale;
                if value <= 0.0 {
                    return Err(format!(
                        "Correlation matrix is not positive definite (failed at diagonal index {i})"
                    ));
                }
                lower[i][j] = value.sqrt();
            } else {
                lower[i][j] = (matrix[i][j] - scale) / lower[j][j];
            }
        }
    }
    Ok(lower)
}

fn parse_spec(data: &[u8]) -> Result<Spec, String> {
    if data.len() < 4 || &data[..4] != b"FPR1" {
        return Err("unrecognized engine spec".to_string());
    }
    let mut reader = Reader::new(&data[4..]);
    let n_assets = reader.u32()? as usize;
    let n_years = reader.u32()? as usize;
    let n_projections = reader.u32()? as usize;
    let start_projection = reader.u32()? as usize;
    if n_assets == 0 {
        return Err("at least one asset is required".to_string());
    }
    if n_assets > 256 {
        return Err("too many assets".to_string());
    }
    if n_years == 0 {
        return Err("horizon must be at least 1 year".to_string());
    }
    let cells = n_projections
        .checked_mul(n_years)
        .ok_or_else(|| "too many projection values".to_string())?;
    if cells > MAX_CELLS {
        return Err("too many projection values".to_string());
    }
    let rng_seed = reader.u64()?;
    let initial_capital = reader.f64()?;
    let cash_buffer = reader.f64()?;
    let liquidity = checked_index(reader.u32()?, n_assets, "liquidity")?;
    let shortfall = checked_index(reader.u32()?, n_assets, "shortfall")?;
    let replenishment = checked_index(reader.u32()?, n_assets, "replenishment")?;

    let n_mix = reader.u32()? as usize;
    if n_mix == 0 {
        return Err("risk mix is empty".to_string());
    }
    let mut mix = Vec::with_capacity(n_mix);
    for _ in 0..n_mix {
        let index = checked_index(reader.u32()?, n_assets, "mix")?;
        mix.push((index, reader.f64()?));
    }

    let mut mu = vec![vec![0.0; n_years]; n_assets];
    let mut sigma = vec![vec![0.0; n_years]; n_assets];
    for asset in 0..n_assets {
        let n_segments = reader.u32()? as usize;
        if n_segments == 0 {
            return Err(format!("asset {asset} has no return distribution"));
        }
        let mut segments = Vec::with_capacity(n_segments);
        for _ in 0..n_segments {
            let from_year = reader.u32()? as usize;
            if from_year < 1 {
                return Err(format!("asset {asset} has from_year {from_year}"));
            }
            segments.push((from_year, reader.f64()?, reader.f64()?));
        }
        let mut filled = vec![false; n_years];
        // Same window walk as init_distrib: later segments in the list are applied
        // first and claim years from their from_year up to the previous boundary.
        let mut upper = n_years + 1;
        for (from_year, seg_mu, seg_sigma) in segments.into_iter().rev() {
            let start = from_year.max(1);
            if start < upper {
                for year in start..upper {
                    if (1..=n_years).contains(&year) {
                        mu[asset][year - 1] = seg_mu;
                        sigma[asset][year - 1] = seg_sigma;
                        filled[year - 1] = true;
                    }
                }
            }
            upper = from_year;
        }
        if filled.iter().any(|ok| !ok) {
            return Err(format!(
                "asset {asset} does not cover every year of the horizon"
            ));
        }
    }

    let n_corr = reader.u32()? as usize;
    let mut matrix = vec![vec![0.0; n_assets]; n_assets];
    for i in 0..n_assets {
        matrix[i][i] = 1.0;
    }
    for _ in 0..n_corr {
        let i = checked_index(reader.u32()?, n_assets, "correlation")?;
        let j = checked_index(reader.u32()?, n_assets, "correlation")?;
        let rho = reader.f64()?;
        matrix[i][j] = rho;
        matrix[j][i] = rho;
    }
    let cholesky = cholesky(&matrix)?;

    let flow_mode = reader.u32()?;
    let per_projection_flows = match flow_mode {
        0 => false,
        1 => true,
        _ => return Err(format!("unknown flow mode {flow_mode}")),
    };
    let n_flows = if per_projection_flows { cells } else { n_years };
    let mut flows = Vec::with_capacity(n_flows);
    for _ in 0..n_flows {
        flows.push(reader.f64()?);
    }
    let (names, csv_path, audit_path, append_outputs) = if reader.at == reader.data.len() {
        (Vec::new(), None, None, false)
    } else {
        let name_count = reader.u32()? as usize;
        if name_count != n_assets {
            return Err(format!(
                "expected {n_assets} asset names, spec has {name_count}"
            ));
        }
        let mut names = Vec::with_capacity(name_count);
        for _ in 0..name_count {
            names.push(reader.string()?);
        }
        let append_outputs = reader.u32()? != 0;
        let csv_path = {
            let path = reader.string()?;
            if path.is_empty() { None } else { Some(path) }
        };
        let audit_path = {
            let path = reader.string()?;
            if path.is_empty() { None } else { Some(path) }
        };
        if reader.at != reader.data.len() {
            return Err("spec has trailing bytes".to_string());
        }
        (names, csv_path, audit_path, append_outputs)
    };

    Ok(Spec {
        n_assets,
        n_years,
        n_projections,
        start_projection,
        rng_seed,
        initial_capital,
        cash_buffer,
        liquidity,
        shortfall,
        replenishment,
        mix,
        mu,
        sigma,
        cholesky,
        per_projection_flows,
        flows,
        names,
        csv_path,
        audit_path,
        append_outputs,
    })
}

fn total(lines: &[f64]) -> f64 {
    let mut value = 0.0;
    for line in lines {
        value += *line;
    }
    value
}

fn rebalance(lines: &mut [f64], mix: &[(usize, f64)]) -> Result<(), String> {
    let mut portfolio_value = 0.0;
    let mut weight = 0.0;
    for (index, mix_weight) in mix {
        portfolio_value += lines[*index];
        weight += *mix_weight;
    }
    if weight == 0.0 {
        return Err("risk mix weights sum to zero".to_string());
    }
    for (index, mix_weight) in mix {
        lines[*index] = portfolio_value * mix_weight / weight;
    }
    Ok(())
}

fn starting_portfolio(spec: &Spec) -> Result<Vec<f64>, String> {
    let mut lines = vec![0.0; spec.n_assets];
    lines[spec.liquidity] = spec.cash_buffer;
    let mut invested = vec![0.0; spec.n_assets];
    invested[spec.mix[0].0] = spec.initial_capital - spec.cash_buffer;
    rebalance(&mut invested, &spec.mix)?;
    for index in 0..spec.n_assets {
        lines[index] += invested[index];
    }
    Ok(lines)
}

fn flows_for<'a>(spec: &'a Spec, projection: usize) -> &'a [f64] {
    if spec.per_projection_flows {
        let start = projection * spec.n_years;
        &spec.flows[start..start + spec.n_years]
    } else {
        &spec.flows
    }
}

struct Outputs {
    names: Vec<String>,
    csv: Option<BufWriter<File>>,
    audit: Option<BufWriter<File>>,
}

fn py_num(value: f64) -> String {
    let text = format!("{value}");
    if text.contains('.') || text.contains('e') || text.contains('E') {
        text
    } else {
        format!("{text}.0")
    }
}

fn write_csv_line(
    csv: &mut BufWriter<File>,
    id: usize,
    period: usize,
    variable: &str,
    risk: &str,
    value: f64,
) -> Result<(), String> {
    writeln!(csv, "{id},{period},{variable},{risk},{}", py_num(value)).map_err(|err| err.to_string())
}

fn write_portfolio(
    csv: &mut BufWriter<File>,
    id: usize,
    period: usize,
    variable: &str,
    names: &[String],
    lines: &[f64],
) -> Result<(), String> {
    for (asset, value) in lines.iter().enumerate() {
        write_csv_line(csv, id, period, variable, &names[asset], *value)?;
    }
    Ok(())
}

fn write_audit_portfolio(
    audit: &mut BufWriter<File>,
    id: usize,
    period: usize,
    names: &[String],
    lines: &[f64],
) -> Result<(), String> {
    writeln!(
        audit,
        "simulation {id} period {period} total {}",
        py_num(total(lines))
    )
    .map_err(|err| err.to_string())?;
    for (asset, value) in lines.iter().enumerate() {
        writeln!(audit, "  {} {}", names[asset], py_num(*value)).map_err(|err| err.to_string())?;
    }
    Ok(())
}

fn run_projection(
    spec: &Spec,
    projection: usize,
    outputs: &mut Outputs,
) -> Result<Vec<f64>, String> {
    let id = spec.start_projection + projection + 1;
    let names = outputs.names.clone();
    let seed = mix_seed(spec.rng_seed, STREAM_RETURNS, id as u64);
    let mut rng = PyRandom::seed_u64(seed);
    let mut lines = starting_portfolio(spec)?;
    if let Some(audit) = outputs.audit.as_mut() {
        write_audit_portfolio(audit, id, 0, &names, &lines)?;
    }
    let flows = flows_for(spec, projection);
    let n = spec.n_assets;
    let mut z = vec![0.0; n];
    let mut returns = vec![0.0; n];
    let mut nav = Vec::with_capacity(spec.n_years);
    let record = outputs.csv.is_some();

    for period in 1..=spec.n_years {
        let flow = flows[period - 1];
        let contributions = flow.max(0.0);
        let withdrawals = (-flow).max(0.0);
        let mut bop = lines.clone();
        bop[spec.liquidity] += contributions;
        let available_cash = bop[spec.liquidity];
        let cash_depletion = withdrawals.min(available_cash);
        let available_after = available_cash - cash_depletion;
        let shortfall = withdrawals - cash_depletion;
        let mut ptf1 = bop.clone();
        ptf1[spec.liquidity] -= cash_depletion;
        ptf1[spec.shortfall] -= shortfall;
        let mut ptf2 = ptf1.clone();
        rebalance(&mut ptf2, &spec.mix)?;
        let value_before_returns = total(&ptf2);

        for shock in &mut z {
            *shock = rng.gauss(0.0, 1.0);
        }
        for asset in 0..n {
            let mut correlated = 0.0;
            for (source, shock) in z.iter().enumerate() {
                correlated += spec.cholesky[asset][source] * shock;
            }
            let year = period - 1;
            returns[asset] =
                (spec.mu[asset][year] + spec.sigma[asset][year] * correlated) / 100.0;
        }
        let mut ptf3 = ptf2.clone();
        for asset in 0..n {
            ptf3[asset] *= 1.0 + returns[asset];
        }
        let gain = total(&ptf3) - value_before_returns;
        let (ptf4, ptf5, cash_replenishment) = if gain > 0.0 {
            let replenishment = (spec.cash_buffer - ptf3[spec.liquidity]).min(gain);
            let mut ptf4 = ptf3.clone();
            ptf4[spec.liquidity] += replenishment;
            ptf4[spec.replenishment] -= replenishment;
            let mut ptf5 = ptf4.clone();
            rebalance(&mut ptf5, &spec.mix)?;
            (ptf4, ptf5, replenishment)
        } else {
            (ptf3.clone(), ptf3.clone(), 0.0)
        };
        let end_value = total(&ptf5);
        nav.push(end_value);

        if record {
            let csv = outputs.csv.as_mut().expect("csv writer");
            write_portfolio(csv, id, period, "ptf_bop", &names, &bop)?;
            write_portfolio(csv, id, period, "ptf_eop", &names, &ptf5)?;
            write_portfolio(csv, id, period, "ptf1", &names, &ptf1)?;
            write_portfolio(csv, id, period, "ptf2", &names, &ptf2)?;
            write_portfolio(csv, id, period, "ptf3", &names, &ptf3)?;
            write_portfolio(csv, id, period, "ptf4", &names, &ptf4)?;
            write_portfolio(csv, id, period, "ptf5", &names, &ptf5)?;
            for asset in 0..n {
                write_csv_line(csv, id, period, "returns", &names[asset], returns[asset])?;
            }
            let scalars = [
                ("contributions", contributions),
                ("withdrawals", withdrawals),
                ("availableCash", available_after),
                ("cashBuffer", spec.cash_buffer),
                ("cashDepletion", cash_depletion),
                ("shortfall", shortfall),
                ("cashReplenishment", cash_replenishment),
                ("financialGainLoss", gain),
            ];
            for (variable, value) in scalars {
                write_csv_line(csv, id, period, variable, "", value)?;
            }
        }
        if let Some(audit) = outputs.audit.as_mut() {
            write_audit_portfolio(audit, id, period, &names, &ptf5)?;
        }
        lines = ptf5;
    }
    Ok(nav)
}

fn open_output(path: &str, append: bool) -> Result<BufWriter<File>, String> {
    let file = if append {
        OpenOptions::new().create(true).append(true).open(path)
    } else {
        File::create(path)
    }
    .map_err(|err| format!("cannot write {path}: {err}"))?;
    Ok(BufWriter::new(file))
}

pub fn run_packed(data: &[u8]) -> Result<Vec<f64>, String> {
    let spec = parse_spec(data)?;
    let mut outputs = Outputs {
        names: spec.names.clone(),
        csv: match &spec.csv_path {
            Some(path) => {
                let mut csv = open_output(path, spec.append_outputs)?;
                if !spec.append_outputs {
                    writeln!(csv, "simulation,period,variable,risk,value")
                        .map_err(|err| err.to_string())?;
                }
                Some(csv)
            }
            None => None,
        },
        audit: match &spec.audit_path {
            Some(path) => {
                let mut audit = open_output(path, spec.append_outputs)?;
                if !spec.append_outputs {
                    writeln!(
                        audit,
                        "rng_seed={} projections={} years={}",
                        spec.rng_seed, spec.n_projections, spec.n_years
                    )
                    .map_err(|err| err.to_string())?;
                }
                Some(audit)
            }
            None => None,
        },
    };
    let mut nav = Vec::with_capacity(spec.n_projections * spec.n_years);
    for projection in 0..spec.n_projections {
        nav.extend(run_projection(&spec, projection, &mut outputs)?);
    }
    if let Some(csv) = outputs.csv.as_mut() {
        csv.flush().map_err(|err| err.to_string())?;
    }
    if let Some(audit) = outputs.audit.as_mut() {
        audit.flush().map_err(|err| err.to_string())?;
    }
    Ok(nav)
}

#[cfg(test)]
mod tests {
    use super::mix_seed;

    #[test]
    fn mix_seed_matches_python() {
        assert_eq!(mix_seed(1, 1, 1), 3706301126960965570);
    }
}
