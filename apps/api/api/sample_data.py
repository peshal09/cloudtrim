"""Bundled demo dataset for the "load sample data" button (BLUEPRINT.md §2).

Embedded as strings (not read from disk) so the sample endpoint works identically
in local dev and in the Docker image, which doesn't copy eval/. The same content
lives in eval/fixtures/demo/ for the eval harness — keep the two in sync.
"""

SAMPLE_TF = """
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
"""

SAMPLE_CSV = """identifier,service,region,instance_type,monthly_cost,cpu_utilization,tags
aws_instance.web,ec2,us-east-1,t3.xlarge,$121.47,4.1,env=prod;owner=team-platform
aws_db_instance.main,rds,us-east-1,db.m5.xlarge,249.66,9.0,env=prod;owner=team-data
i-0deadbeef42,ec2,us-east-1,t3.large,60.74,0.0,env=prod
"""

SAMPLE_K8S = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: default
spec:
  replicas: 6
  template:
    metadata:
      labels:
        app: web
        env: prod
    spec:
      containers:
        - name: web
          image: acme/web:1.0
          resources:
            requests:
              cpu: "500m"
              memory: "256Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
  namespace: default
spec:
  selector:
    app: web
---
apiVersion: v1
kind: Service
metadata:
  name: legacy-svc
  namespace: default
spec:
  selector:
    app: legacy
"""

# Six months of spend with a clear S3 spike in the last period (anomaly demo).
SAMPLE_HISTORY = """period,service,cost
2026-01,ec2,1200.00
2026-02,ec2,1255.00
2026-03,ec2,1180.00
2026-04,ec2,1230.00
2026-05,ec2,1245.00
2026-06,ec2,1265.00
2026-01,rds,800.00
2026-02,rds,810.00
2026-03,rds,795.00
2026-04,rds,805.00
2026-05,rds,815.00
2026-06,rds,820.00
2026-01,s3,150.00
2026-02,s3,162.00
2026-03,s3,155.00
2026-04,s3,158.00
2026-05,s3,152.00
2026-06,s3,890.00
"""
