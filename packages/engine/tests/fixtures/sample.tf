resource "aws_instance" "web" {
  instance_type = "t3.large"
  region        = "us-east-1"
  tags = {
    env  = "prod"
    Name = "web"
  }
}

resource "aws_db_instance" "main" {
  instance_class = "db.t3.medium"
  tags = {
    env = "prod"
  }
}

resource "aws_s3_bucket" "logs" {
  bucket = "my-logs-bucket"
}
