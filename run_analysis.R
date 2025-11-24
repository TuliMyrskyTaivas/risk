# Check if packages are installed (without loading them)
using <- function(...) {
  libs <- unlist(list(...))
  installed <- libs %in% installed.packages()[, "Package"]
  need <- libs[!installed]

  if (length(need) > 0)
    install.packages(need, repos = "https://mirror.truenetwork.ru/CRAN/")
}

# Check for the required libraries
using(
  "DBI",
  "dplyr",
  "readr",
  "tidyr",
  "tibble",
  "logger",
  "lubridate",
  "RSQLite",
  "PerformanceAnalytics"
)

# Load function
source("src/returns.R")
source("src/weights.R")
source("src/portfolio.R")

prepare_performance_data <- function(weights, returns) {
  # weights: the weights_vector from above function
  # returns: xts object with historical returns (columns matching weight names)
  if (!all(names(weights) %in% colnames(returns))) {
    warning("Some assets in portfolio not found in returns data")
  }

  # Align weights with available returns data
  assets <- names(weights)[names(weights) %in% colnames(returns)]
  aligned_weights <- weights[assets]

  return(list(
    weights = aligned_weights,
    returns = returns[, assets]
  ))
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
  stop("Pass to the portfolio file have to be specified", call. = FALSE)
}

portfolio <- load_portfolio_data(args[1])
on.exit(DBI::dbDisconnect(portfolio$db))

# Calculate logarithmic returns
log_returns <- calculate_log_returns(portfolio$db)

# Calculate weights
weights <- calculate_portfolio_weights(portfolio$assets)

# Calculate historical returns
perf_data <- prepare_performance_data(weights$weights_vector, log_returns)
portfolio_returns <- PerformanceAnalytics::Return.portfolio(perf_data$returns,
                                                            weights = perf_data$weights)

# Calculate VaR
historical_var <- PerformanceAnalytics::VaR(portfolio_returns,
                                            p = 0.95,
                                            method = "historical",
                                            portfolio_method = "single") * weights$total_portfolio_value
# Calculate the expected shortfall
es <- PerformanceAnalytics::ES(portfolio_returns, p = 0.95) * weights$total_portfolio_value
mean <- mean(portfolio_returns)
volatility <- sd(portfolio_returns)
skewness <- PerformanceAnalytics::skewness(portfolio_returns)
kurtosis <- PerformanceAnalytics::kurtosis(portfolio_returns)
logger::log_info("Historical VaR: {historical_var}")
logger::log_info("Expected shortfall: {es}")
logger::log_info("Mean: {mean}")
logger::log_info("Volatility: {volatility}")
logger::log_info("Skewness: {skewness}")
logger::log_info("Kurtosis: {kurtosis}")