resource "aws_instance" "a" {
  instance_type = "t3.2xlarge"
  tags = {
    env   = "prod"
    owner = "team-platform"
  }
}

# config-only (no billing row) — oversized-in-IaC smell, no runtime data
resource "aws_instance" "b" {
  instance_type = "c5.2xlarge"
  tags = {
    env   = "prod"
    owner = "team-batch"
  }
}

resource "aws_s3_bucket" "data" {
  bucket = "acme-prod-data"
  tags = {
    env   = "prod"
    owner = "team-data"
  }
}
