# A well-configured stack — no waste. Precision guard: any finding here is a
# false positive and fails the eval.
resource "aws_instance" "api" {
  instance_type = "t3.medium"
  tags = {
    env   = "prod"
    owner = "team-platform"
  }
}

resource "aws_db_instance" "db" {
  instance_class = "db.t3.medium"
  tags = {
    env   = "prod"
    owner = "team-data"
  }
}

resource "aws_s3_bucket" "assets" {
  bucket = "acme-prod-assets"
  lifecycle_rule {
    enabled = true
  }
  tags = {
    env   = "prod"
    owner = "team-platform"
  }
}
