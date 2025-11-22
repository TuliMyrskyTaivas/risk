calculate_portfolio_weights <- function(portfolio) {  
  # Clean column names
  colnames(portfolio) <- gsub(" ", "_", colnames(portfolio))  

  # Calculate total portfolio value
  total_portfolio_value <- sum(portfolio$Current_value, na.rm = TRUE)

  # Calculate weights
  portfolio$Weight <- portfolio$Current_value / total_portfolio_value

  # Create weights vector for PerformanceAnalytics (named by ISIN)
  weights_vector <- portfolio$Weight[!is.na(portfolio$Code)]
  # Use ISIN codes as names
  names(weights_vector) <- portfolio$Code[!is.na(portfolio$Code)]

  # Create compatible data frame
  asset_weights <- data.frame(
    Code = portfolio$Code,
    Name = portfolio$Name,
    Weight = round(portfolio$Weight * 100, 2),  # Percentage
    Current_Value = portfolio$Current_value,
    stringsAsFactors = FALSE
  )

  # Sort by weight
  asset_weights <- asset_weights[order(-asset_weights$Weight), ]

  return(list(
    total_portfolio_value = total_portfolio_value,
    weights_vector = weights_vector,  # This is PerformanceAnalytics compatible
    asset_weights = asset_weights
  ))
}