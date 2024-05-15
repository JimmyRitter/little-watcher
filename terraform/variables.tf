locals {
  # Terraform to read .env values, having all configurations in one place
  envs = { for tuple in regexall("(.*)=(.*)", file("../.env")) : tuple[0] => sensitive(tuple[1]) }
}

# locals {
#   envs = { 
#     for tuple in regexall("\\s*([^#=\\s]+)\\s*=\\s*\"?([^#\\n\"]+)\"?\\s*", file("../.env")) : 
#     tuple[0] => tuple[1] 
#   }
# }