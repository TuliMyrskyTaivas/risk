calculate_portfolio_weights <- function(portfolio) {
  `%>%` <- dplyr::`%>%`

  # Clean column names
  colnames(portfolio) <- gsub(" ", "_", colnames(portfolio))

  assets <- portfolio %>% filter(!is.na(Code) & Code != "")

  # Calculate total portfolio value
  total_value <- sum(assets$Current_value, na.rm = TRUE)

  # Calculate weights
  assets$Weight <- assets$Current_value / total_value

  # Create weights vector for PerformanceAnalytics (named by ISIN)
  weights_vector <- assets$Weight
  # Use ISIN codes as names
  names(weights_vector) <- assets$Code

  return(list(
    total_portfolio_value = total_value,
    weights_vector = weights_vector
  ))
}