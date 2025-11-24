# Read assets info
load_portfolio_data <- function(file) {
  library(readr, warn.conflicts = FALSE, quietly = TRUE)
  library(dplyr, warn.conflicts = FALSE, quietly = TRUE)
  library(stringr)

  assets <- read_csv2(args[1],
                      trim_ws = TRUE,
                      show_col_types = FALSE,
                      locale = locale(
                        decimal_mark = ",",
                        grouping_mark = " ",
                        encoding = "UTF-8"
                      ),
                      col_types = cols(
                                       Name = col_character(),
                                       Type = col_character(),
                                       Code = col_character(),
                                       Broker = col_character(),
                                       Amount = col_number(),
                                       Currency = col_character(),
                                       "Book price" = col_number(),
                                       "Current price" = col_number(),
                                       "Book value" = col_number(),
                                       "Current value" = col_number(),
                                       "P/L" = col_number(),
                                       Return = col_number(),
                                       Yield = readr::col_number()))
  # Read ISIN codes skipping empty (NA/NULL) values
  tickers <- assets$Code[!is.na(assets$Code)]
  logger::log_info("{NROW(tickers)} assets with ISIN code in the portfolio")

  # Get DB cache
  db <- DBI::dbConnect(RSQLite::SQLite(), dbname = "data/cache.db")

  # Calculate preliminary date range (for the worst case if we do not
  # have any data at all)
  end_date <- as.Date(lubridate::now())
  begin_date <- as.Date(end_date - lubridate::years(1))
  logger::log_info("Loading the pricing data in rage {begin_date}/{end_date}")

  # Check if data table exists and get latest date to begin with
  if (DBI::dbExistsTable(db, "data")) {
    # Get the maximum date from existing data
    latest_date_query <- "SELECT MAX(begin) as latest_date FROM data"
    latest_date_result <- DBI::dbGetQuery(db, latest_date_query)
    latest_date <- latest_date_result$latest_date[1]

    # If there's existing data, start from the day after latest date
    if (!is.na(latest_date)) {
      begin_date <- as.Date(as.POSIXct(latest_date))
    }
  }

  logger::log_info("Latest record in the database: {begin_date}")

  begin_date <- begin_date + lubridate::days(1)
  # Only download new data if begin_date is not in the future
  if (begin_date <= lubridate::now()) {
    logger::log_info("Querying MOEX on prices from {begin_date}...")
    # Get historical data for the missing period
    new_data <- moexer::get_candles(tickers, from = begin_date,
                                    interval = "daily")

    # Append new data to existing table
    if (nrow(new_data) > 0) {
      logger::log_info("{nrow(new_data)} new items available")
      print(new_data)
      if (DBI::dbExistsTable(db, "data")) {
        DBI::dbWriteTable(db, "data", as.data.frame(new_data),
                          append = TRUE, row.names = FALSE)
      } else {
        copy_to(db, new_data, temporary = FALSE, name = "data")
      }
      logger::log_info("Added {nrow(new_data)} new rows to the database")
    } else {
      logger::log_info("No new data available")
    }
  } else {
    logger::log_info("Database is already up to date")
  }

  list(db = db, assets = assets)
}