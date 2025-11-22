calculate_log_returns <- function(db_connection, price_table = "data") {
  `%>%` <- dplyr::`%>%`

  # Read price data
  price_data <- DBI::dbGetQuery(db_connection, 
                                paste("SELECT * FROM", price_table))

  if (nrow(price_data) == 0) {
    warning("No price data found")
    return(NULL)
  }

  # Convert to wide format
  price_wide <- price_data %>%
    dplyr::select(begin, secid, close) %>%
    # Convert Unix timestamp to Date - adjust column name if needed
    dplyr::mutate(date = as.Date(as.POSIXct(begin, origin = "1970-01-01"))) %>%
    dplyr::select(date, secid, close) %>%
    tidyr::pivot_wider(
      names_from = secid,
      values_from = close,
      values_fill = NA
    ) %>%
    dplyr::arrange(date) %>%
    tibble::column_to_rownames("date")

  # Ensure we have at least 2 rows for return calculation
  if (nrow(price_wide) < 2) {
    warning("Insufficient data points for return calculation")
    return(NULL)
  }

  # Calculate logarithmic returns
  log_returns <- tryCatch({
    na.omit(PerformanceAnalytics::Return.calculate(price_wide, method = "log"))
  }, error = function(e) {
    warning("Error calculating returns: ", e$message)
    return(NULL)
  })

  if (!is.null(log_returns)) {
    # Convert to long format
    log_returns_long <- log_returns %>%
      as.data.frame() %>%
      tibble::rownames_to_column("date") %>%
      tidyr::pivot_longer(
        cols = -date,
        names_to = "code",
        values_to = "log_return"
      )

    # return(log_returns_long)
    return(log_returns)
  } else {
    return(NULL)
  }
}