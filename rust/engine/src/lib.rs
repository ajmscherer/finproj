mod engine;
mod py_random;

use std::os::raw::c_char;
use std::panic::{AssertUnwindSafe, catch_unwind};

fn write_err(buf: *mut u8, cap: usize, message: &str) {
    if buf.is_null() || cap == 0 {
        return;
    }
    let bytes = message.as_bytes();
    let n = bytes.len().min(cap - 1);
    unsafe {
        std::ptr::copy_nonoverlapping(bytes.as_ptr(), buf, n);
        *buf.add(n) = 0;
    }
}

/// Run the packed spec. On success, `*out_nav` is `*out_count` little-endian
/// f64s (projection-major, year within projection) and the caller frees them
/// with `finproj_free`. On failure returns 1 and writes a C string into `err_buf`.
#[unsafe(no_mangle)]
pub extern "C" fn finproj_run(
    spec: *const u8,
    spec_len: usize,
    out_nav: *mut *mut f64,
    out_count: *mut usize,
    err_buf: *mut c_char,
    err_cap: usize,
) -> i32 {
    if !out_nav.is_null() {
        unsafe { *out_nav = std::ptr::null_mut() };
    }
    if !out_count.is_null() {
        unsafe { *out_count = 0 };
    }
    if spec.is_null() || out_nav.is_null() || out_count.is_null() {
        write_err(err_buf as *mut u8, err_cap, "null argument");
        return 1;
    }
    let bytes = unsafe { std::slice::from_raw_parts(spec, spec_len) };
    let result = catch_unwind(AssertUnwindSafe(|| engine::run_packed(bytes)));
    let nav = match result {
        Ok(Ok(nav)) => nav,
        Ok(Err(message)) => {
            write_err(err_buf as *mut u8, err_cap, &message);
            return 1;
        }
        Err(_) => {
            write_err(err_buf as *mut u8, err_cap, "rust engine panicked");
            return 1;
        }
    };
    let mut nav = nav;
    let count = nav.len();
    let ptr = nav.as_mut_ptr();
    std::mem::forget(nav);
    unsafe {
        *out_nav = ptr;
        *out_count = count;
    }
    0
}

/// Release a buffer returned by `finproj_run`.
#[unsafe(no_mangle)]
pub extern "C" fn finproj_free(ptr: *mut f64, count: usize) {
    if ptr.is_null() || count == 0 {
        return;
    }
    unsafe {
        let _ = Vec::from_raw_parts(ptr, count, count);
    }
}
