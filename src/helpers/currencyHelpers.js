/**
 * Philippine Peso Currency Formatting Utilities
 * Simple helpers for PHP currency formatting with commas and 2 decimal places
 */

/**
 * Formats a number as Philippine Peso currency
 * @param {number|string} value - The value to format
 * @returns {string} Formatted currency string (e.g., "₱1,234.56")
 */
export function formatCurrency(value) {
  if (value === null || value === undefined || isNaN(value)) {
    return '₱0.00'
  }

  const numericValue = parseFloat(value)
  
  return `₱${numericValue.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`
}

/**
 * Formats a number with thousand separators (no currency symbol)
 * @param {number|string} value - The value to format
 * @returns {string} Formatted number string (e.g., "1,234")
 */
export function formatNumber(value) {
  if (value === null || value === undefined || isNaN(value)) {
    return '0'
  }

  const numericValue = parseFloat(value)
  return numericValue.toLocaleString('en-US')
}