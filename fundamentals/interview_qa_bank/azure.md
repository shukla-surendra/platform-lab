# Azure Questions and Answers

**Q1: Explain the benefits of Azure?**

A: Azure is a cloud computing platform providing computing, analytics, storage, and networking services. Key benefits include Scalability (easily adjust replicas based on demand), Cost-Effectiveness (pay only for usage), Flexibility (supports multiple operating systems, programming languages, frameworks), and Disaster Recovery (comprehensive backup and recovery solutions).

**Q2: Explain some Azure Cloud Services?**

A: Azure Cloud Services are PaaS offerings enabling developers to build and deploy applications without managing underlying infrastructure. Key services include Azure Virtual Machines, App Services, and Azure Functions.

**Q3: What are the various models available for cloud deployment?**

A: Three primary models exist: Public Cloud (services over public internet shared across multiple users), Private Cloud (dedicated services to a single organization hosted on-premises or in a third-party data center), and Hybrid Cloud (combines public and private clouds enabling data and application sharing).

**Q4: Why is Azure Diagnostics APIs needed?**

A: Azure Diagnostics APIs collect and store diagnostic data such as logs and metrics from applications running in Azure. They help monitor performance, identify issues, and maintain application health.

**Q5: Define Azure Service Level Agreements (SLA)?**

A: Azure SLAs are formal documents defining performance and availability standards that Azure services must meet. They specify uptime guarantees and provide remedies or compensations if standards aren't met.

**Q6: What is Azure Resource Manager?**

A: Azure Resource Manager (ARM) is the deployment and management service for Azure, enabling consistent creation, updating, and deletion of resources. Key features include Resource Groups (organize related resources), ARM Templates (automated deployments via Infrastructure as Code), Role-Based Access Control (RBAC), Tagging Support, and Centralized Management.

**Q7: What is NSG?**

A: NSG stands for Network Security Group, a feature in Azure providing control over inbound and outbound traffic to and from Azure resources. It allows users to define security rules filtering traffic based on IP address, port, and protocol.

**Q8: What is Azure Redis Cache?**

A: Azure Redis Cache is a fully managed, in-memory data store based on open-source Redis. Features include In-Memory Storage (ultra-fast operations), Caching Layer (reduces latency), High Availability (replication, clustering, failover), Scalability, and seamless Integration with Azure applications.

**Q9: Define Azure Virtual Machine Scale Sets.**

A: Azure virtual machine scale sets are a service in Azure that allows creating and managing a group of identical, balanced VMs. They facilitate automatic scaling of VM numbers in response to demand, ensuring high availability and performance.

**Q10: What do you understand about the "Availability Set"?**

A: An Availability Set is a logical grouping of VMs ensuring high availability. It protects applications from planned or unplanned maintenance by distributing VMs across Fault Domains (safeguard hardware failures) and Update Domains (stagger updates). Azure guarantees 99.95% uptime for VMs in an Availability Set.

**Q11: What is the difference between Availability Zones and Availability Sets?**

A: Availability Zones are physically separate data centers within the same region with independent power, cooling, and networking, protecting against complete data center failures. Availability Sets are logical VM groupings within a single data center distributing across Fault and Update Domains, protecting against hardware failures and planned maintenance but not complete outages.

**Q12: What are the differences between Azure Scale Sets and Availability Sets?**

A: Scale Sets automatically adjust VM numbers based on demand (elastic scaling), while Availability Sets distribute a fixed VM set across fault/update domains for redundancy (high availability).

**Q13: What is Azure Kubernetes Service (AKS), and how is it different from Azure Container Instances (ACI)?**

A: AKS is a managed Kubernetes service supporting container orchestration, scaling, and load balancing for production applications. ACI is a serverless container execution service running individual containers without managing VMs or clusters, best for short-lived tasks and simple applications.

**Q14: What are the available options for deployment environments provided by Azure?**

A: Options include Azure Virtual Machines (full OS control), Azure App Service (PaaS for web apps), Azure Kubernetes Service (containerized applications at scale), Azure Functions (serverless, event-driven), Azure Container Instances (quick deployment), and Azure Batch (large-scale parallel computing).

**Q15: What are Deployment Slots in Azure App Service, and how do they enable Blue-Green deployment?**

A: Deployment Slots are separate live instances of an App Service app (e.g., staging, production) that share the same app resources but can run different code versions. New versions deploy to staging, then a slot swap routes traffic to the new version with minimal downtime.

**Q16: What do you need to do when drive failure occurs?**

A: Ensure regular backups are in place and use Azure Site Recovery or other replication services to restore data and minimize downtime.

**Q17: Is it possible to design an application that handles the connection failure in Azure?**

A: Yes. Applications can implement retry logic (exponential backoff), use Azure's fault-tolerant services, and leverage Azure Traffic Manager or Front Door for failover.

**Q18: Define Azure Storage Key.**

A: An Azure Storage Key is a security credential authenticating access to an Azure Storage account. Two keys (primary and secondary) enable redundancy and key rotation without downtime.

**Q19: What is cspack in Azure?**

A: The cspack is a command-line tool used for generating service package files for deployment to Azure Cloud Services. It packages application binaries, configuration files, and resources into deployment format.

**Q20: What is the best Azure Solution for executing the code without a server?**

A: Azure Functions is the best solution — a serverless computing environment for running event-driven code without managing infrastructure. Payment is based on execution time (Consumption plan) or pinned capacity (Premium/Dedicated plans).

**Q21: What would be the best feature recommended by Azure for having a common file-sharing system between multiple virtual machines?**

A: Azure File Share is the best feature, providing fully managed cloud file shares accessible via SMB protocol by multiple VMs.

**Q22: What is the difference between Azure Logic Apps and Azure Functions?**

A: Azure Logic Apps is a low-code/no-code workflow automation service using visual designers with hundreds of built-in connectors, best for business process automation. Azure Functions is serverless compute supporting multiple languages, triggered by events, best for custom business logic and event-driven applications.

**Q23: Is it possible to log in to a Linux Virtual Machine without using a password?**

A: Yes, through SSH key-based authentication. Generate an SSH key pair, add the public key to the VM, disable password authentication in sshd_config, and connect using the private key: `ssh -i /path/to/private_key user@vm-ip`.

**Q24: What are the instance types offered by Azure?**

A: Azure offers General Purpose (balanced CPU-to-memory, D-series), Compute Optimized (high CPU-to-memory ratio, F-series), Memory Optimized (high memory-to-CPU ratio, E-series), Storage Optimized (high disk throughput, L-series), and GPU (graphics rendering, N-series) instance types.

**Q25: What feature of Azure can be used to stop the issue of high load on the application in cases of no man support on the flow?**

A: Azure Auto-Scaling helps manage high load by automatically adjusting the number of running instances based on predefined metrics and thresholds, ensuring performance without manual intervention.

**Q26: What are the advantages of scaling in Azure?**

A: Improved application performance and availability, cost efficiency (pay only for usage), automatic workload adjustment, and enhanced fault tolerance and redundancy.

**Q27: What is Azure Blob Storage?**

A: Azure Blob Storage is a service for storing large amounts of unstructured data such as text, binary data, images, and videos. It's highly scalable and accessible over HTTP/HTTPS.

**Q28: What storage services does Azure provide apart from Blob Storage?**

A: Table Storage (NoSQL key-value store for structured data), Queue Storage (message queuing between components), and File Storage (managed file shares via SMB protocol).

**Q29: What are the differences between Azure Table Storage and the Azure SQL service?**

A: Azure Table Storage is NoSQL, schema-less, storing semi-structured data using PartitionKey and RowKey, highly scalable for logs and IoT data. Azure SQL Database is relational, schema-based, supporting SQL queries and transactions, best for structured business data.

**Q30: What are the differences between Azure Storage Queue and Azure Service Bus Queue?**

A: Azure Storage Queue is simple, low-cost, supporting basic FIFO processing for background tasks. Azure Service Bus Queue is enterprise-grade, supporting guaranteed ordering, transactions, duplicate detection, and dead-letter queues for complex enterprise applications.

**Q31: What is the difference between Azure Backup and Azure Site Recovery?**

A: Azure Backup creates scheduled backups for data recovery from deletion or corruption. Azure Site Recovery (ASR) continuously replicates VMs to another region supporting automatic failover, minimizing downtime during disasters.

**Q32: What is Federation in Azure SQL?**

A: Federation in Azure SQL (now called Elastic Scale) allows horizontal partitioning (sharding) of data across multiple databases, improving performance and manageability for very large datasets.

**Q33: What is Azure Cosmos DB, and what are its consistency levels?**

A: Azure Cosmos DB is Azure's globally distributed, multi-model NoSQL database service, guaranteeing single-digit-millisecond latency and 99.999% availability. Five consistency levels exist: Strong (linearizable reads, highest consistency), Bounded Staleness (configurable lag), Session (within-session consistency, default), Consistent Prefix (no out-of-order writes), and Eventual (lowest latency).

**Q34: What is the difference between Azure Virtual Network (VNet) and Azure ExpressRoute? When is each used?**

A: Azure VNet is a private network enabling secure Azure resource communication with subnets, NSGs, and peering. Azure ExpressRoute provides a dedicated private on-premises-to-Azure connection bypassing the public internet, offering lower latency and higher security for hybrid deployments.

**Q35: What is the difference between Azure Load Balancer, Application Gateway, Traffic Manager, and Front Door?**

A: Azure Load Balancer distributes Layer 4 (TCP/UDP) traffic among regional VMs. Application Gateway provides Layer 7 (HTTP/HTTPS) routing with SSL termination and WAF. Traffic Manager routes DNS-based global traffic across endpoints. Front Door is a global Layer 7 load balancer with CDN and WAF integration.

**Q36: Differentiate between repetitive and minimal monitoring approaches.**

A: Repetitive Monitoring continuously monitors at frequent intervals with detailed logs, detecting issues quickly for production environments. Minimal Monitoring tracks only key metrics and critical events with lower overhead, suitable for development or low-priority workloads.

**Q37: What is Microsoft Entra ID (formerly Azure Active Directory)?**

A: In 2023, Microsoft rebranded Azure Active Directory (Azure AD) to Microsoft Entra ID as part of unifying its identity products under the Microsoft Entra family. The service, APIs, SLAs, pricing, and capabilities remain unchanged; only the product name changed.

**Q38: What are the benefits of using Azure AD (Microsoft Entra ID) in hybrid environments?**

A: Provides a Single Identity Platform simplifying user management across on-premises and cloud resources, enables Single Sign-On (SSO) reducing repeated credential entry, and offers Seamless Integration synchronizing on-premises AD with Entra ID.

**Q39: How does Azure Active Directory (Microsoft Entra ID) integrate with on-premises Active Directory?**

A: Azure AD Connect (Entra Connect) synchronizes on-premises AD objects (users, groups, attributes) with Entra ID for consistency. Password Hash Synchronization syncs password hashes enabling same-credential sign-in. Pass-through Authentication (PTA) authenticates directly against on-premises AD without cloud password storage.

**Q40: What happens when the maximum failed sign-in attempts are reached during Azure AD authentication?**

A: Azure AD (Entra ID) enforces security measures such as account lockout (Smart Lockout) or triggering multi-factor authentication (MFA) to mitigate brute-force attacks and unauthorized access attempts.

**Q41: What is Azure Key Vault?**

A: Azure Key Vault is a centralized cloud service for securely storing and managing secrets, encryption keys, and certificates. Features include secrets management (API keys, connection strings), key management (encryption keys), certificate management (SSL/TLS), access control integration with RBAC, and full auditing logging.

**Q42: What is a Managed Identity in Azure? What's the difference between System-assigned and User-assigned?**

A: A Managed Identity is an automatically-managed Entra ID identity letting Azure resources authenticate to other services without storing credentials. System-assigned identities are created automatically tied to resource lifecycle, assigned to one resource. User-assigned identities are separate resources with independent lifecycle, assignable to multiple resources.

**Q43: What is the difference between RBAC and Azure Policy?**

A: Azure RBAC manages user permissions to Azure resources using roles controlling who performs which actions. Azure Policy enforces organizational standards evaluating resource properties during creation/updates, allowing, denying, auditing, or modifying configurations for compliance.

**Q44: What is the role of Azure Monitor and Azure Log Analytics in managing Azure resources?**

A: Azure Monitor is the umbrella monitoring service — collects, analyzes, and acts on telemetry (metrics, logs, activity data) across Azure resources. Azure Log Analytics is Monitor's component where log data centralizes, stores, and queries using KQL for deep analysis.

**Q45: Write a sample KQL (Kusto Query Language) query used in Azure Monitor Log Analytics.**

A: A sample query finding the top 10 slowest App Service requests in 24 hours:
```kql
AppRequests
| where TimeGenerated > ago(24h)
| where Success == false or DurationMs > 2000
| project TimeGenerated, Name, Url, DurationMs, ResultCode
| top 10 by DurationMs desc
```

**Q46: What is Azure DevOps? What are its core services?**

A: Azure DevOps is Microsoft's suite of tools supporting the full DevOps lifecycle — planning, developing, testing, and deploying software. Core services: Azure Repos (Git/TFVC source control), Azure Pipelines (CI/CD automation), Azure Boards (work tracking), Azure Artifacts (package management), Azure Test Plans (testing tools).

**Q47: What are the differences between ARM Templates, Bicep, and Terraform for Infrastructure as Code?**

A: ARM Templates are native Azure IaC in JSON (declarative, verbose). Bicep is Azure-native using concise syntax, compiling to ARM, easier maintenance. Terraform is open-source, cloud-agnostic HCL-based supporting multiple platforms with state management.

**Q48: What was Azure Scheduler, and what replaced it?**

A: Azure Scheduler historically created scheduled HTTP/S endpoint calls or queue messages. Functionality migrated to Azure Logic Apps (Recurrence trigger) or Azure Functions (Timer trigger).

**Q49: How do you create Azure resources using the Azure CLI? Give sample commands.**

A: Sample commands:
```bash
az group create --name myResourceGroup --location eastus
az vm create --resource-group myResourceGroup --name myVM --image Ubuntu2204 --admin-username azureuser --generate-ssh-keys
az storage account create --name mystorageacct123 --resource-group myResourceGroup --location eastus --sku Standard_LRS
```

**Q50: Explain the failover procedure in Azure when the primary server goes down in a hybrid environment.**

A: Failover redirects traffic from primary to secondary Azure-hosted servers using Azure Traffic Manager (DNS-based), Azure Load Balancer (traffic distribution), Application Gateway (application-level routing), or Azure Site Recovery (automated VM failover).

**Q51: In a scenario where the application front end is hosted on Azure but the database must remain on-premises due to security concerns, how is connectivity managed?**

A: Connectivity uses VNet Peering (Azure-to-Azure), Azure VPN Gateway (encrypted internet connection), or Azure ExpressRoute (dedicated private connection bypassing public internet).

**Q52: What is the difference between IaaS, PaaS, and SaaS? Where does Azure fit?**

A: IaaS provides virtualized computing (VMs, storage, networking) with the customer managing OS and applications. PaaS provides managed development platforms with the provider managing infrastructure. SaaS provides fully managed software over the internet. Azure fits across all models with VMs (IaaS), App Service (PaaS), and Microsoft 365 (SaaS).

**Q53: What are the data redundancy (replication) options in Azure Storage?**

A: LRS (Locally Redundant Storage) maintains 3 copies in a single data center. ZRS (Zone-Redundant Storage) spreads 3 copies across Availability Zones. GRS (Geo-Redundant Storage) replicates LRS to a secondary region asynchronously. RA-GRS adds read access to the secondary region. GZRS/RA-GZRS combines ZRS with geo-replication.

**Q54: What are the types of Azure Managed Disks?**

A: Standard HDD (lowest cost, backups), Standard SSD (consistent latency, web servers), Premium SSD (high-performance production workloads), and Ultra Disk (highest performance, databases).

**Q55: What is the difference between NSG, Application Security Group (ASG), and Azure Firewall?**

A: NSG filters inbound/outbound network traffic via subnets or NICs using IP/port/protocol rules. ASG logically groups VMs simplifying NSG rule management. Azure Firewall is a fully managed, stateful service protecting multi-VNet traffic with application/network/NAT rules.

**Q56: What is Azure Bastion?**

A: Azure Bastion is a fully managed PaaS service that provides secure RDP/SSH connectivity to VMs directly through the Azure portal, over TLS, without exposing the VM's public IP address. It eliminates jump box VMs and reduces attack surface.

**Q57: What is the difference between Azure Private Endpoint, Private Link, and Service Endpoint?**

A: Service Endpoint extends VNet identity to Azure services over the Azure backbone with public endpoint access restricted by firewall. Private Endpoint provisions a private IP inside a VNet for PaaS resources. Private Link is the underlying technology powering Private Endpoints, enabling private PaaS connectivity.

**Q58: What is the difference between Azure Event Grid, Event Hubs, and Service Bus?**

A: Event Grid routes events from Azure services to subscribers via push delivery for serverless architectures. Event Hubs ingests millions of events per second for real-time analytics via pull-based consumption. Service Bus provides enterprise messaging via queues/topics with transactions, sessions, and duplicate detection.

**Q59: What are Azure App Service Plan pricing tiers?**

A: Free/Shared (development/testing, shared infrastructure), Basic (dedicated compute, manual scaling), Standard (adds auto-scaling and deployment slots), Premium (more scale-out and slots), Isolated (dedicated ASE inside VNet, maximum isolation).

**Q60: How do you manage and optimize Azure costs? (Cost Management, Tags, Advisor)**

A: Azure Cost Management + Billing provides spend analysis dashboards with budget alerts. Resource Tags (key-value metadata) enable cost attribution by resource/tag. Azure Advisor recommends cost optimization, performance, security, and reliability improvements.

**Q61: What are Resource Locks in Azure?**

A: Resource Locks prevent accidental deletion or modification of critical resources regardless of RBAC permissions. CanNotDelete allows reading/modification but prevents deletion. ReadOnly permits only reading.

**Q62: What are Azure Spot VMs and Reserved Instances? How do they help reduce cost?**

A: Azure Spot VMs purchase unused capacity at ~90% discount but risk eviction when capacity is needed, suitable for interruptible workloads. Reserved Instances commit to 1-3 year terms for ~72% discounts, suitable for steady-state production workloads.

Note: only the following 15 have complete answers available; additional related questions beyond these were not accessible.

**Q63: What are the core components of Microsoft Azure's architecture?**

A: Azure's architecture rests on: the Management Plane (Azure Resource Manager handles provisioning and resource lifecycle), the Control Plane (ARM + Azure Policy enforce defined state and conformance), the Data Plane (services like Blob Storage and Cosmos DB regulate the flow of user data), a Global Network (Azure's low-latency, high-bandwidth backbone), Identity (Azure AD authenticates and authorizes users and services), Security & Compliance (dedicated teams manage regulatory compliance), and Billing (metered, usage-based). Core areas of focus layered on top: IaaS (e.g. Azure VMs), PaaS (e.g. Azure App Service), SaaS (e.g. Office 365), and Serverless Computing (Azure Functions, Logic Apps).

**Q64: Explain the difference between Infrastructure as a Service (IaaS) and Platform as a Service (PaaS).**

A: IaaS offers versatile networking/storage/virtualization with the user responsible for most of the OS, application, and security stack — best for organizations needing specialized software stacks or full system control (e.g. legacy migrations). PaaS streamlines development/deployment workflows with the cloud provider absorbing infrastructure management — best for standardized, collaborative dev environments and faster time-to-market. Both models share responsibility between provider and user, just at different layers.

**Q65: What is Azure Resource Manager and how does it benefit Azure resource management?**

A: ARM is a management framework for deploying, managing, and organizing Azure resources. Benefits: consistent lifecycle management across resources; ARM Templates for declarative, repeatable, version-controlled deployments; RBAC integration for precise access control; policy enforcement for compliance; grouping/tagging for logical organization; visual management via Portal/CLI/PowerShell; cost aggregation and billing by resource group; Resource Locks (CanNotDelete / ReadOnly) to prevent accidental changes; and extensibility for custom resources.

**Q66: Describe the main categories of services offered by Azure.**

A: IaaS (Virtual Machines, Blob Storage, Virtual Network, Load Balancer, Site Recovery) gives the fundamental building blocks with the user managing the OS/apps. PaaS (App Service, Azure SQL Database, Azure AD, Cosmos DB) frees developers from infrastructure management. SaaS (Office 365, Dynamics 365, Azure Automation) delivers ready-to-use software over the internet. Shared services (Key Vault, Azure AD, API Management) cut across all three, handling security, identity, and automation.

**Q67: Explain the use of Azure regions and availability zones.**

A: Regions are separate geographical areas hosting datacenters; availability zones are unique, fault-isolated datacenters within a region providing added stability and redundancy. They're used for service proximity (lower latency), disaster recovery, and redundancy — enabling hybrid deployments across regions, meeting data-residency/compliance requirements, robust backup/recovery strategies, and serving a geographically distributed customer base.

**Q68: How does Azure ensure data redundancy and failover?**

A: Data replication strategies: LRS (3 copies within one data center), ZRS (3 copies synchronously across availability zones in a region), GRS (asynchronous replication to a secondary region for disaster protection). Automatic failover is handled by services like Azure Traffic Manager (routes across distributed endpoints), Azure SQL Database (automatic database failover across the global data center presence), Azure Redis Cache (primary/secondary cache pair in a paired region), and Blob Storage with GRS/RA-GRS (automatic failover to the paired secondary region). Best practice: design for resiliency with redundant components across zones/regions and run regular disaster-recovery drills.

**Q69: In what scenarios would you use Azure App Service Environment?**

A: App Service Environment (ASE) provides a dedicated, network-isolated platform for web apps/APIs/backends when you need: high security/compliance (finance, healthcare, government — FIPS, PCI DSS, HIPAA), a unified experience across public/private/hybrid networks (secure access to databases/storage without exposing them publicly), custom VNet integration with advanced network configuration, or static outbound IP addresses for consistent outbound traffic.

**Q70: What is the Azure Service Level Agreement (SLA) and how does it impact application design?**

A: Azure SLAs guarantee a monthly uptime percentage per service (with service credits for underperformance if not met); some categories have a single SLA tier, others have multiple tiers by pricing plan, and some services have no defined SLA at all. To meet SLA-aligned availability, application design should incorporate: redundancy/distributed data (geo-redundant storage, instance replication), regional deployment (minimize latency, survive regional outages), load balancing (Traffic Manager/Load Balancer), auto-scaling for traffic fluctuations, health monitoring (Azure Monitor/App Insights), data backups/recovery, and fault-tolerant patterns (e.g. serverless Functions).

**Q71: Describe the difference between Azure Classic and Azure Resource Manager deployment models.**

A: Classic (1st-gen) manages resources individually in a "flat" model, typically via command-line tools, with no built-in resilience/versioning and manual networking. ARM uses a "container-based," hierarchical model (resource groups) with bulk configuration and RBAC across groups, declarative JSON templates defining an entire environment, built-in versioning/rollback support, simplified VNet/subnet configuration, stronger governance via Azure Policy, and consolidated cost management/billing at the resource-group level.

**Q72: Explain the concept of Azure Resource Groups.**

A: Resource Groups are logical containers for managing and deploying related resources (web apps, databases, VMs, etc.) together. Key features: grouping, tagging for tracking/billing, access control applied at the group level, and unified resource lifecycle management (deleting a group terminates everything in it). Benefits include simplified organization/security, simultaneous deployment of related resources, cost efficiency/reporting, unified monitoring, and automation. Constraints: a group is limited to roughly 800 resources (varies by subscription/resource type), and some resource types (e.g. Azure AD resources) fall outside a group's scope. Best practice: group resources by shared lifecycle and use tags for organization.

**Q73: When should you choose Azure Functions over Azure App Service?**

A: Choose Azure Functions for event-driven, lightweight operations (file manipulation, DB updates, API calls), small specialized functions in microservice architectures, infrequent/sporadic workloads (cost-effective since billing is per-execution), quick prototyping, and integration with managed services like Event Hubs/Service Bus/Blob Storage. Choose Azure App Service for standard web applications/REST APIs, continuous workflows handling HTTP requests or CRON-scheduled tasks, full customization/framework flexibility, and consistently high-throughput applications needing predictable, scalable performance. Cost-wise, Functions charge per execution/time/resource consumption (with a free monthly allocation); App Service charges by pricing tier, which is more cost-efficient for consistently high-throughput apps.

**Q74: Describe how you would scale an Azure Virtual Machine.**

A: Vertical scaling re-deploys the VM on a larger size — good for I/O-bound tasks needing faster CPU/more RAM, but limited by the maximum VM size available. Horizontal scaling uses Azure Virtual Machine Scale Sets to add more VM instances — better for web apps, multi-tier apps, and high-CPU worker tasks. VM families come in General Purpose (balanced), Memory-Optimized, Storage-Optimized, and GPU-Enabled variants; both OS and data disks can be scaled up (e.g. HDD to SSD) as needed. Autoscaling can be triggered via Azure Monitor/Alerts (metric-based, e.g. CPU/RAM thresholds) or time-based schedules (e.g. scale up during business hours), and Scale Sets can be load-balanced via Azure Load Balancer (Layer 4) or Application Gateway (Layer 7, for HTTP/HTTPS with SSL termination and path-based routing).

**Q75: What are the different types of Azure Virtual Machines available and how do you choose one?**

A: VM families: General Purpose (balanced CPU-to-memory, for dev/test/production), Compute-Optimized (high CPU-to-memory, for analytics/gaming/media processing), Memory-Optimized (high memory-to-core ratio, for SAP HANA/SQL Hekaton/data-intensive apps), and Storage-Optimized (high throughput/low latency, for Big Data/NoSQL like MongoDB/Cassandra). Choice depends on workload requirements (CPU/memory/disk needs), budget, expected scalability/growth, and ongoing performance monitoring via Azure Monitor. Available sizes/specs can be inspected via the Portal ("Size" under Settings) or CLI (`az vm list-sizes --location <location> --resource-group <rg> --name <vm>`) / PowerShell (`Get-AzureRmVMSize`).

**Q76: Explain the purpose of Azure Batch service.**

A: Azure Batch handles large-scale compute-intensive tasks by orchestrating work across a dynamically-managed pool of compute nodes. Core components: Pools (groups of VMs for task execution, self-managed or Batch-managed), Jobs (a set of independently schedulable tasks), and Tasks (individual units of work). Capabilities include dynamic scaling of the VM pool based on demand (cost-effective, no paying for idle VMs), application lifecycle management across nodes, flexible task scheduling/dependencies, security/compliance integration, detailed monitoring/logging, multi-region global scale, and hybrid deployment via VNet integration. Use cases: large dataset/ETL processing, rendering, HPC (physics simulations, weather forecasting), ML model training at scale, and financial modeling (e.g. Monte Carlo simulations).

**Q77: How do you deploy a Docker container to Azure Container Instances?**

A: Create a resource group, then deploy with `az container create` (uploads the Docker image to an Azure-managed registry), and view output with `az container logs`. Example:
```bash
az login
az group create --name myResourceGroup --location eastus

az container create \
  --resource-group myResourceGroup \
  --name mycontainer \
  --image mydockerimage \
  --cpu 1 \
  --memory 1.5Gi \
  --registry-username <username> \
  --registry-password <password>

az container logs --resource-group myResourceGroup --name mycontainer
az container delete --resource-group myResourceGroup --name mycontainer
```
Security consideration: never hard-code registry credentials in scripts — use Azure Key Vault instead. The same deployment can also be done through the Azure Portal's "Container Instances" blade.
