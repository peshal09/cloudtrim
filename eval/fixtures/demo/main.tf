resource "aws_instance" "web" {
  instance_type = "t3.xlarge"
  tags = {
    env   = "prod"
    owner = "team-platform"
    Name  = "web"
  }
}

resource "aws_instance" "batch" {
  instance_type = "c5.4xlarge"
  tags = {
    env  = "prod"
    Name = "batch"
  }
}

resource "aws_db_instance" "main" {
  instance_class = "db.m5.xlarge"
  tags = {
    env   = "prod"
    owner = "team-data"
  }
}

resource "aws_s3_bucket" "logs" {
  bucket = "acme-prod-logs"
  tags = {
    env   = "prod"
    owner = "team-platform"
  }
}
