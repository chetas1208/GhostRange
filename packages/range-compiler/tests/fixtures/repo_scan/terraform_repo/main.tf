resource "aws_db_instance" "primary" {
  engine = "postgres"
}

resource "aws_lb" "app_lb" {
  internal = false
}
