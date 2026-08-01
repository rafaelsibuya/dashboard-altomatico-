use pyo3::prelude::*;
use pyo3::types::PyBytes;

/// Valida se os bytes passados representam um arquivo XLSX válido (assinatura ZIP: PK\x03\x04).
#[pyfunction]
fn validate_excel_file(file_bytes: &PyBytes) -> PyResult<bool> {
    let bytes = file_bytes.as_bytes();
    
    // Um arquivo XLSX é basicamente um ZIP. A assinatura do ZIP (Magic Number) é 50 4B 03 04.
    if bytes.len() < 4 {
        return Ok(false);
    }
    
    // PK\x03\x04
    if bytes[0] == 0x50 && bytes[1] == 0x4B && bytes[2] == 0x03 && bytes[3] == 0x04 {
        Ok(true)
    } else {
        Ok(false)
    }
}

/// Um módulo Python implementado em Rust.
#[pymodule]
fn rust_security(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate_excel_file, m)?)?;
    Ok(())
}
