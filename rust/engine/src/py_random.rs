//! CPython's `random.Random` (MT19937 + `gauss`), so a finproj seed draws
//! the same returns as `inv_proj.py` on this machine.

const N: usize = 624;
const M: usize = 397;
const MATRIX_A: u32 = 0x9908b0df;
const UPPER_MASK: u32 = 0x80000000;
const LOWER_MASK: u32 = 0x7fffffff;

pub struct PyRandom {
    mt: [u32; N],
    index: usize,
    gauss_next: Option<f64>,
}

impl PyRandom {
    pub fn seed_u64(n: u64) -> Self {
        let mut rng = Self {
            mt: [0; N],
            index: N,
            gauss_next: None,
        };
        if n == 0 {
            rng.init_by_array(&[0]);
        } else if n <= u32::MAX as u64 {
            rng.init_by_array(&[n as u32]);
        } else {
            rng.init_by_array(&[n as u32, (n >> 32) as u32]);
        }
        rng.gauss_next = None;
        rng
    }

    fn init_genrand(&mut self, seed: u32) {
        self.mt[0] = seed;
        for mti in 1..N {
            let prev = self.mt[mti - 1];
            self.mt[mti] = 1812433253u32
                .wrapping_mul(prev ^ (prev >> 30))
                .wrapping_add(mti as u32);
        }
        self.index = N;
    }

    fn init_by_array(&mut self, key: &[u32]) {
        self.init_genrand(19650218);
        let key_length = key.len();
        let mut i = 1usize;
        let mut j = 0usize;
        let mut k = if N > key_length { N } else { key_length };
        while k > 0 {
            let prev = self.mt[i - 1];
            self.mt[i] = (self.mt[i] ^ (prev ^ (prev >> 30)).wrapping_mul(1664525))
                .wrapping_add(key[j])
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
            if j >= key_length {
                j = 0;
            }
            k -= 1;
        }
        k = N - 1;
        while k > 0 {
            let prev = self.mt[i - 1];
            self.mt[i] = (self.mt[i] ^ (prev ^ (prev >> 30)).wrapping_mul(1566083941))
                .wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
            k -= 1;
        }
        self.mt[0] = 0x80000000;
    }

    fn genrand_uint32(&mut self) -> u32 {
        if self.index >= N {
            for kk in 0..(N - M) {
                let y = (self.mt[kk] & UPPER_MASK) | (self.mt[kk + 1] & LOWER_MASK);
                let mag = if y & 1 == 0 { 0 } else { MATRIX_A };
                self.mt[kk] = self.mt[kk + M] ^ (y >> 1) ^ mag;
            }
            for kk in (N - M)..(N - 1) {
                let y = (self.mt[kk] & UPPER_MASK) | (self.mt[kk + 1] & LOWER_MASK);
                let mag = if y & 1 == 0 { 0 } else { MATRIX_A };
                self.mt[kk] = self.mt[kk - (N - M)] ^ (y >> 1) ^ mag;
            }
            let y = (self.mt[N - 1] & UPPER_MASK) | (self.mt[0] & LOWER_MASK);
            let mag = if y & 1 == 0 { 0 } else { MATRIX_A };
            self.mt[N - 1] = self.mt[M - 1] ^ (y >> 1) ^ mag;
            self.index = 0;
        }
        let mut y = self.mt[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;
        y
    }

    pub fn random(&mut self) -> f64 {
        let a = (self.genrand_uint32() >> 5) as f64;
        let b = (self.genrand_uint32() >> 6) as f64;
        (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)
    }

    pub fn gauss(&mut self, mu: f64, sigma: f64) -> f64 {
        let z = if let Some(z) = self.gauss_next.take() {
            z
        } else {
            let x2pi = self.random() * (2.0 * std::f64::consts::PI);
            let g2rad = (-2.0 * (1.0 - self.random()).ln()).sqrt();
            let z = x2pi.cos() * g2rad;
            self.gauss_next = Some(x2pi.sin() * g2rad);
            z
        };
        mu + z * sigma
    }
}

#[cfg(test)]
mod tests {
    use super::PyRandom;

    fn assert_close(actual: f64, expected: f64) {
        assert!((actual - expected).abs() < 1e-12, "{actual} != {expected}");
    }

    #[test]
    fn random_matches_cpython_seed_1() {
        let mut rng = PyRandom::seed_u64(1);
        assert_close(rng.random(), 0.13436424411240122);
    }

    #[test]
    fn gauss_matches_cpython_seed_1() {
        let expected = [
            1.2881847531554629,
            1.4494456086997711,
            0.06633580893826191,
            -0.7645436509716318,
            -1.0921732151041414,
            0.03133451683171687,
            -1.022103170010873,
            -1.4368294451025299,
        ];
        let mut rng = PyRandom::seed_u64(1);
        for value in expected {
            assert_close(rng.gauss(0.0, 1.0), value);
        }
    }

    #[test]
    fn gauss_matches_cpython_wide_seed() {
        let expected = [
            -1.010597665013166,
            0.25575320524021716,
            -2.5305702933145238,
            1.6254444961169838,
            -0.5791995698011748,
            -0.2888646187822342,
        ];
        let mut rng = PyRandom::seed_u64(3706301126960965570);
        for value in expected {
            assert_close(rng.gauss(0.0, 1.0), value);
        }
    }
}
