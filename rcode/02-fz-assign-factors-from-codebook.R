library(dplyr)

data <- tribble(
  ~var,
  1,
  2,
  3,
  4
)

# codebook should be a "long" data frame with a mapping between:
# var_name, value, label
dict <- tribble(
  ~var_name, ~value, ~label,
  'var', 1, 'A',
  'var', 2, 'B',
  'var', 3, 'C',
  'var', 4, 'D'
)

#
for (n in names(data)){
  temp <- filter(dict, var_name == n) 
  data[[n]] <- factor(data[[n]], levels = temp$value, labels = temp$label)
}

# code_as_factors <- function(df, mapping, var_name_col="var_name", level_col="value", label_col="label"){
#   # copy
#   df_out <- df
#   for (n in names(df_out)){
#     print(n)
#     temp <- filter(mapping, var_name_col == n) 
#     df_out[[n]] <- factor(df_out[[n]], levels = temp[, level_col], labels = temp[, label_col])
#     print(temp[, level_col])
#     print(temp[, label_col])
#   }
#   return(df_out)
# }
# 
# code_as_factors(df=data, mapping=dict)

data
dict
names(data)
dict[, "label"]
