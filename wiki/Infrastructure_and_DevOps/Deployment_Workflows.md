---
tags: [infrastructure, devops, deployment, heroku]
date_created: 2026-04-12
sources:
  - "[[Akitando 112 - Subindo Aplicações Web em Produção]] (Clipper)"
  - "[[Akitando 139 - Entendendo Como Containers Funcionam]] (Clipper)"
---
# Deployment Workflows

Modern software deployment has evolved from manual server configuration (LAMP stack) to automated, container-based "Cloud Native" workflows.

## Infrastructure as Code (IaC)
To avoid manual configuration errors and ensure environment reproducibility, modern infrastructure is defined as code.

### Terraform
An industry-standard IaC tool for provisioning hardware and cloud resources (IaaS).
- **Provider-Agnostic**: Can manage resources across AWS, GCP, Azure, and more.
- **Declarative**: You define the "desired state" (e.g., "I want a VPC with 3 subnets and an RDS instance"), and Terraform calculates the necessary steps to reach that state.
- **Workflow**:
    1. `terraform init`: Download necessary provider plugins.
    2. `terraform plan`: Preview changes without applying them (reproducibility).
    3. `terraform apply`: Execute the changes in the cloud provider.
- **Terraform vs. Kubernetes**: Terraform works at a lower level (provisioning the servers, network, and managed databases), while Kubernetes operates at a higher level (managing the containers running on those servers).

## The Traditional Paradigm (LAMP)
- **Stack**: Linux, Apache, MySQL, Perl/PHP.
- **Workflow**: Files uploaded via FTP/SFTP directly to a production VPS (e.g., Linode).
- **Risks**: Manual configuration drift, no easy rollback, and "works on my machine" syndrome due to lack of environment parity.

## The Heroku Paradigm (PaaS)
Heroku revolutionized deployment by abstracting infrastructure into an automated Git-based workflow.

### Key Concepts
- **Buildpacks**: Scripts that detect the application language (Ruby, Node, PHP) and provision the necessary runtime and dependencies. A precursor to the Dockerfile concept.
- **Dynos**: Isolated, ephemeral Linux containers where the application runs.
- **Procfile**: A simple text file in the repository root that defines the process types (e.g., `web`, `worker`).
- **Releases**: Every successful build creates a numbered release. This allows for near-instant **Rollbacks** if a bug is detected in production.
- **Ephemeral Filesystem**: Dynos are recycled frequently; any data written to the local disk is lost. Persistent data must be stored in external volumes or databases.

### Deployment Workflow
1. **Git Push**: `git push heroku main` triggers the build process.
2. **Dependency Resolution**: Buildpacks run `npm install`, `composer update`, or `bundle install` based on **Lock Files**.
3. **Execution**: The `web` process defined in the `Procfile` is started.
4. **Load Balancing**: Heroku's internal proxy routes traffic to active dynos.

## The 12-Factor App Methodology
A set of principles for building scalable, maintainable, and portable software-as-a-service (SaaS) applications.
- **Codebase**: One codebase tracked in revision control, multiple deploys.
- **Dependencies**: Explicitly declare and isolate dependencies (using lock files).
- **Config**: Store configuration (secrets, API keys) in **Environment Variables** (Config Vars), never in the code.
- **Backing Services**: Treat databases, queues, and caches as attached resources.
- **Build, Release, Run**: Strictly separate the build and execution stages.
- **Processes**: Run the app as one or more stateless processes.
- **Port Binding**: Export services via port binding.
- **Concurrency**: Scale out via the process model (adding more dynos).
- **Disposability**: Fast startup and graceful shutdown (SIGTERM) for robustness.
- **Dev/Prod Parity**: Keep development, staging, and production as similar as possible.
- **Logs**: Treat logs as event streams (standard output) and aggregate them (e.g., Papertrail).
- **Admin Processes**: Run admin/management tasks as one-off processes in the same environment.

## Quality Assurance: Performance and Load Testing

Successful deployment requires validating that the infrastructure can sustain the expected "ramp-up" of users.

### Benchmarking Tools
- **Gatling**: A high-performance tool using Scala/Kotlin DSLs. Excellent for complex scenarios and generating visual reports.
- **Vegeta**: A constant-rate HTTP load testing tool. Useful for finding the breaking point of a service.
- **Apache Bench (`ab`)**: The "Old Guard" tool for quick, simple concurrency testing.
- **WRK**: A modern, multi-threaded benchmarking tool.

### Statistical Literacy: Beyond the Average
When interpreting load test results, relying on the **Mean (Average)** is misleading because it hides the **Tail Latency** (the experience of the most frustrated users).
- **50th Percentile (Median)**: The middle ground. 50% of users had a faster experience, 50% slower. Represents the "typical" user.
- **95th Percentile**: Only 5% of users experienced a slower response. Highly indicative of system stability under stress.
- **99th Percentile**: The extreme edge cases. Often caused by garbage collection pauses, network hiccups, or resource saturation. In a microservices architecture, the 99th percentile of one service often becomes the bottleneck for the entire system.

### Benchmarking-Driven Decisions
Avoid "premature optimization" and "gut-feeling" changes.
- **Identify the True Bottleneck**: Is it the Database (SQL locks), the CPU (complex logic), or the Network (Docker NAT overhead)?
- **Quantify Improvements**: An optimization is only valid if it demonstrably lowers the 95th/99th percentile without compromising the code's maintainability.

## Importance of Dependency Management
A core tenet of modern deployment is the use of **Lock Files** (`package-lock.json`, `composer.lock`, `Gemfile.lock`, `Cargo.lock`).
- **Reproducibility**: Ensures every environment (Dev, Staging, Production) runs the exact same version of every library.
- **Security**: Prevents unauthorized "pushed" updates from introducing malicious code or breaking changes during a fresh install.
