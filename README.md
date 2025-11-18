# Kabob Store - AWS ECS Fargate Application using Amazon Aurora DSQL Multi-regional database

A complete cloud-native kabob takeout store application built with AWS ECS Fargate, featuring a Python FastAPI backend and React frontend, with global data storage using a Amazon Aurora DSQL Multi-regional database.

## Architecture

- **Frontend**: React.js application served via Nginx
- **Backend**: Python FastAPI application
- **Database**: AWS Aurora DSQL (multi-region distributed SQL database)
- **Infrastructure**: AWS ECS Fargate with Application Load Balancer
- **Container Registry**: Amazon ECR
- **Infrastructure as Code**: Terraform

## Features

- Full-featured kabob store interface
- Multi-region footprint with Aurora DSQL distributed database
- Containerized microservices architecture
- Serverless compute with AWS Fargate
- Security best practices with VPC and security groups
- CloudWatch logging and monitoring
- Auto-scaling capabilities

## Project Structure

```
.
├── infrastructure/           # Infrastructure as Code
│   ├── main.tf              # Main Terraform configuration
│   ├── variables.tf         # Terraform variables
│   ├── outputs.tf           # Terraform outputs
│   ├── vpc.tf               # VPC and networking
│   ├── security-groups.tf   # Security group configurations
│   ├── iam.tf               # IAM roles and policies
│   ├── ecr.tf               # ECR repositories
│   ├── dsql.tf              # Aurora DSQL database configuration
│   ├── alb.tf               # Application Load Balancer
│   ├── ecs.tf               # ECS cluster and services
│   ├── modules/             # Reusable Terraform modules
│   └── environments/        # Environment-specific configurations
├── backend/                 # Python FastAPI backend
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Backend container
└── frontend/                # React frontend
    ├── src/                 # React source code
    ├── public/              # Public assets
    ├── package.json         # Node.js dependencies
    ├── Dockerfile           # Frontend container
    └── nginx.conf           # Nginx configuration
```

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform
- Docker
- Node.js (for local development)
- Python 3.11+ (for local development)

## Deployment

### 1. Infrastructure Deployment

```bash
# Navigate to infrastructure directory
cd infrastructure

# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy all infrastructure including multi-region DSQL clusters
terraform apply
```

This creates:
- Multi-region DSQL clusters (primary in us-east-1, secondary in us-east-2, witness in us-west-2)
- VPC and networking
- ECS cluster and services
- Application Load Balancer
- ECR repositories
- IAM roles and policies

**Note**: The infrastructure uses the official `terraform-aws-modules/rds-aurora` DSQL module which supports multi-region clusters.

### 2. Container Image Build and Push

After infrastructure deployment, build and push your container images:

```bash
# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(terraform -chdir=infrastructure output -raw ecr_backend_repository_url | cut -d'/' -f1)

# Build and push backend image
cd backend
docker build -t kabob-store-backend .
docker tag kabob-store-backend:latest <backend-ecr-url>:latest
docker push <backend-ecr-url>:latest

# Build and push frontend image
cd ../frontend
docker build -t kabob-store-frontend .
docker tag kabob-store-frontend:latest <frontend-ecr-url>:latest
docker push <frontend-ecr-url>:latest
```

### 3. Update ECS Services

After pushing new images, update the ECS services to deploy the new containers:

```bash
# Update backend service
aws ecs update-service --cluster kabob-store-cluster --service kabob-store-backend-service --force-new-deployment

# Update frontend service
aws ecs update-service --cluster kabob-store-cluster --service kabob-store-frontend-service --force-new-deployment
```

## Configuration

### Environment Variables

The application uses the following environment variables:

**Backend:**
- `DSQL_CLUSTER_IDENTIFIER`: Aurora DSQL cluster identifier
- `DATABASE_NAME`: Database name
- `AWS_REGION`: AWS region

**Frontend:**
- `REACT_APP_API_URL`: Backend API URL (set to ALB DNS name)

### Customization

You can customize the deployment by modifying the variables in `variables.tf`:

- `aws_region`: AWS region for deployment
- `project_name`: Name prefix for all resources
- `vpc_cidr`: VPC CIDR block
- `backend_cpu`/`backend_memory`: Backend container resources
- `frontend_cpu`/`frontend_memory`: Frontend container resources

## API Endpoints

The backend provides the following REST API endpoints:

- `GET /health` - Health check endpoint
- `GET /api/menu` - Get all menu items
- `POST /api/menu` - Create a new menu item
- `GET /api/menu/{id}` - Get specific menu item
- `POST /api/orders` - Create a new order
- `GET /api/orders` - Get all orders
- `GET /api/orders/{id}` - Get specific order

## Security Features

- VPC with public and private subnets
- Security groups with least privilege access
- ECS tasks in private subnets
- ALB in public subnets for external access
- IAM roles with minimal required permissions
- ECR image scanning enabled
- CloudWatch logging for monitoring

## Multi-Region Architecture

The application uses Amazon Aurora DSQL multi-region cluster for a distributed SQL database with active-active multi-region support. The infrastructure deploys:

- **Primary Cluster**: us-east-1 (configurable via `aws_region` variable)
- **Secondary Cluster**: us-east-2 (configurable via `secondary_region` variable)
- **Witness Region**: us-west-2 (configurable via `witness_region` variable) - *Note: This is a configuration setting for quorum, not an actual cluster*

DSQL provides automatic multi-region replication, strong consistency, and low-latency access for users. The multi-region cluster configuration ensures high availability and disaster recovery capabilities without the complexity of managing regional clusters or replication topology.

**Important**: You will only see DSQL clusters in us-east-1 and us-east-2. The witness region (us-west-2) is a configuration setting that designates a third region to maintain quorum for strong consistency - it does not create a separate cluster.

## Monitoring and Logging

- CloudWatch log groups for both frontend and backend
- Container insights enabled on ECS cluster
- ALB access logs (can be enabled)
- ECR vulnerability scanning

## Cleanup

To destroy the infrastructure:

```bash
cd infrastructure
terraform destroy
```

## Development

For local development:

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Support

This infrastructure supports:
- Auto-scaling based on CPU/memory utilization
- Blue-green deployments
- Rolling updates
- Health checks and automatic recovery
- Multi-AZ deployment for high availability

## Cost Optimization

- Use Fargate Spot pricing where appropriate
- ECR lifecycle policies to manage image storage costs
- CloudWatch log retention policies
- Right-sized compute resources

## Read More
This repository is associated with the following blog https://darryl-ruggles.cloud/dsql-kabob-store
