# Google Cloud Platform (GCP) Questions and Answers

**Q1: What is Google Cloud Platform (GCP)?**

A: Google offers an assortment of cloud computing services using the Google Cloud Platform (GCP) name. It delivers machine learning, storage, and computational capabilities for application development. GCP includes global network support and is engineered for security and performance across all organizational sizes.

**Q2: Name some core services provided by GCP?**

A: Primary services include Compute Engine for virtual machines, Cloud Storage for scalable object storage, BigQuery for data warehousing and analytics, and Kubernetes Engine for container orchestration.

**Q3: What is Google Compute Engine?**

A: Using Google Compute Engine (GCE), consumers may create and manage virtual machines on Google's infrastructure utilizing a cloud-based service. It offers scalable computing power, supports various operating systems, and integrates with other Google Cloud services while providing reliability and flexibility.

**Q4: Explain the purpose of Google Cloud Storage?**

A: A service for storing and accessing data on Google's infrastructure is Google Cloud Storage. It provides scalable, secure, and permanent storage options for structured and unstructured data, allowing users to save and retrieve objects of any size through an easy API.

**Q5: What is the GCP resource hierarchy, and why does it matter?**

A: GCP resources are organized in a hierarchy: Organization → Folders → Projects → Resources (VMs, buckets, databases, etc.). IAM policies inherit downward, enabling large companies to manage access and billing at scale without configuring each project individually.

**Q6: How are GCP projects typically organized?**

A: A GCP project is the base unit for enabling APIs, managing billing, and applying IAM permissions — every resource you create belongs to exactly one project. Teams commonly separate projects by purpose or environment (compute, storage, analytics, machine learning) for easier billing and access control.

**Q7: How do you create a new project in GCP?**

A: Navigate to console.cloud.google.com, select "New Project," enter the project name, specify the location or organization, choose a billing account, then click "Create" to complete configuration.

**Q8: What is Google App Engine?**

A: A number of Google Cloud's fully managed platform-as-a-service (PaaS) products is Google App Engine. It enables developers to build and execute scalable web services, handling scaling, load balancing, and monitoring while supporting Go, Java, Python, and Node.js.

**Q9: What is the difference between a region and a zone in GCP?**

A: In Google Cloud Platform (GCP), a Region is a geographical location containing multiple isolated Zones, whereas a Zone is an individual deployment area within a region where cloud resources such as virtual machines are hosted.

**Q10: How does Google Cloud IAM help manage access?**

A: Centralized control over who has access to specific assets is made feasible by Google Cloud IAM (Identity and Access Management). It enables granular access control through users, groups, and service accounts while enforcing least privilege principles and providing comprehensive audit capabilities.

**Q11: What are the different types of IAM roles in GCP?**

A: GCP has three categories: Basic (Primitive) roles — Owner, Editor, and Viewer (broad, legacy, discouraged in production), Predefined roles (curated by Google for specific services like storage.objectViewer), and Custom roles (built by picking exact permissions).

**Q12: What is a service account, and how is it different from a user account?**

A: A service account is a special type of identity that applications, VMs, or workloads use to authenticate and call GCP APIs — it doesn't belong to a person. Unlike user accounts, service accounts authenticate using keys or Workload Identity, avoiding long-lived credential exports.

**Q13: What is a VPC (Virtual Private Cloud)?**

A: Within a cloud environment, a virtual network dedicated to a specific company is called a Virtual Private Cloud (VPC). It offers isolated resources with restricted access and security instructions, enabling organizations to create logically isolated cloud infrastructure portions.

**Q14: What is a firewall rule in GCP, and how does it control traffic?**

A: A firewall rule in Google Cloud Platform (GCP) is a set of criteria that dictates which incoming and outgoing network traffic is allowed to reach or leave VM instances. Rules control traffic based on IP addresses, protocols, and ports.

**Q15: What is the Function of a Bucket in Google Cloud Storage?**

A: Google Cloud Storage buckets are core containers used to store and manage data such as files, images, and backups with high scalability, durability, and security. They support flexible storage classes, location options, and fine-grained access control.

**Q16: What are the different Cloud Storage classes, and when should you use each?**

A: Cloud Storage offers four classes: Standard (for frequently accessed "hot" data), Nearline (for data accessed less than once a month), Coldline (for data accessed less than once a quarter), and Archive (the cheapest option, for data accessed less than once a year).

**Q17: What are the connections between Google Compute Engine and Google App Engine?**

A: GCE offers customizable VMs for full control, while App Engine provides fully managed, auto-scaling deployment. They work together through seamless networking, enabling hybrid deployments where GAE handles frontend APIs and GCE manages databases and high-performance computing.

**Q18: Explain the purpose and use of Google Kubernetes Engine (GKE)?**

A: Google Kubernetes Engine (GKE) is a fully managed platform for deploying, managing, and scaling containerized applications using Kubernetes. It automates cluster management, supports auto-scaling and load balancing, and enables efficient production deployment of cloud-native applications.

**Q19: What is Google Cloud Run, and how does it relate to Cloud Functions?**

A: Cloud Run is a fully managed serverless platform for running stateless containers — you package your application as a container image, and Cloud Run automatically scales it up and down (including to zero) based on incoming requests. Unlike Cloud Functions, it isn't language-restricted.

**Q20: How do you choose between Compute Engine, App Engine, GKE, Cloud Run, and Cloud Functions?**

A: Choose Compute Engine for full OS control, App Engine for traditional web apps without infrastructure management, GKE for Kubernetes-based multi-container orchestration, Cloud Run for serverless containerized services, and Cloud Functions for small event-driven code snippets.

**Q21: What are Google Cloud Functions, and when would you use them?**

A: Cloud Functions let you run small pieces of code in response to events — an HTTP request, a file landing in Cloud Storage, a Pub/Sub message, a Firestore write — without provisioning or managing any servers. They're ideal for lightweight, event-driven tasks.

**Q22: How do you configure autoscaling in GCP?**

A: Navigate to Compute Engine, select the instance group, enable autoscaling, choose scaling metrics (CPU utilization, load balancing), configure minimum and maximum instances, and GCP automatically adjusts based on workload demand.

**Q23: What is Google Cloud Pub/Sub, and how does it work?**

A: A messaging service for event-driven systems is Google Cloud Pub/Sub. Topics are conduits for distributing data; publishers communicate messages to these topics, and subscribers receive messages from these topics. It uses a push-pull model.

**Q24: Describe how to set up a Cloud SQL instance?**

A: Open Google Cloud Console, navigate to SQL, click Create Instance, choose database engine (MySQL, PostgreSQL, SQL Server), configure instance ID, region, machine type, storage, and networking, then click Create for automatic provisioning.

**Q25: What is Cloud Spanner, and how is it different from Cloud SQL?**

A: Cloud Spanner is Google's fully managed, horizontally scalable relational database that combines the consistency and structure of a traditional SQL database. Cloud SQL scales vertically; Cloud Spanner scales horizontally and offers 99.999% uptime SLA.

**Q26: What is the difference between Persistent Disk and Local SSD in GCP?**

A: Persistent Disk is network-attached block storage with data persisting even after VM stops, while Local SSD is physically attached to the host machine with extremely high IOPS and low latency but ephemeral data lost on VM termination.

**Q27: What is the difference between a disk snapshot and a custom image in GCP?**

A: Disk Snapshot is a backup of a Persistent Disk used for recovery, while Custom Image is a template created from a boot disk or VM used for launching multiple instances with identical configuration.

**Q28: How do you use Stackdriver for monitoring and logging in GCP?**

A: Enable Stackdriver Monitoring and Logging APIs, set up dashboards and alerts for resource metrics, submit application logs to Stackdriver Logging for analysis and searching, use Stackdriver Trace for distributed tracing, and configure appropriate IAM permissions.

**Q29: Explain the role of BigQuery in GCP?**

A: BigQuery is the entirely managed serverless data storage solution offered by Google Cloud Platform. It enables rapid analysis of huge data sets using SQL-like queries, provides real-time analytics, integrates with other GCP services, and offers cost-effective pay-as-you-go billing.

**Q30: What is the difference between Cloud Dataflow and Cloud Dataproc?**

A: Cloud Dataflow is a fully managed and serverless data processing service using Apache Beam, supporting batch and stream processing without cluster management. Cloud Dataproc is a managed service for open-source big data frameworks supporting Spark and Hadoop with cluster management.

**Q31: What is the principle of least privilege, and how do you apply it in GCP?**

A: Due to the least privilege principle, users ought to receive only the bare minimum of access necessary to do their tasks. In GCP, this is implemented through IAM by granting specific roles with precise permissions, limiting unauthorized access risks.

**Q32: Describe the process of setting up a VPN between on-premises network and GCP?**

A: Establish a VPN gateway in GCP, connect the on-premises VPN device to the GCP gateway through an encrypted connection, configure firewall rules allowing communications, ensure proper routing configuration, and test the connection for effective data transmission.

**Q33: What is Cloud NAT, and why would you use it?**

A: Cloud NAT (Network Address Translation) lets VM instances or GKE pods that don't have external IP addresses initiate outbound connections to the internet without exposing them to unsolicited inbound traffic. It's the standard pattern for keeping backend instances private.

**Q34: Explain the concept of uptime checks and how they contribute to monitoring in GCP?**

A: GCP uptime checks are automated tests that maintain a watch on a resource's or service's availability. They send ongoing requests to endpoints, helping maintain reliability and enabling timely issue resolution by detecting outages and performance problems proactively.

**Q35: How do you optimize the cost of running workloads in GCP?**

A: Use sustained use and committed use discounts for predictable workloads, use Spot VMs for fault-tolerant batch jobs, enable autoscaling to avoid idle capacity, use lifecycle rules for cheaper storage classes, and leverage cost tools (Billing reports, Budgets, Pricing Calculator).

**Q36: Explain the concept of Infrastructure as Code (IaC) in GCP and tools you can use?**

A: Configuration files are employed in Google Cloud Platform (GCP) Infrastructure as Code (IaC) to manage and provision cloud resources. Essential tools include Terraform, Ansible, and Google Cloud Deployment Manager for declarative resource management and automation.

**Q37: How would you design a highly available and scalable architecture in GCP?**

A: Use global load balancers distributing traffic across regions, deploy instances across multiple zones with autoscaling, utilize managed services (Cloud SQL, BigQuery, Firebase), combine Cloud Storage with CDN for global content delivery, and maintain continuous monitoring.

**Q38: Describe a multi-cloud strategy and how you can implement it using GCP?**

A: A multi-cloud approach involves making use of different cloud services from different providers to improve redundancy, decrease expenses, and prevent vendor lock-in. Use BigQuery Omni, Apigee, Anthos, GKE, and VPC peering for cross-cloud integration.

**Q39: What is Cloud Key Management Service (Cloud KMS), and how does it relate to encryption in GCP?**

A: Cloud KMS is GCP's managed service for creating, storing, rotating, and controlling access to cryptographic keys. While GCP encrypts all data at rest using Google-managed keys by default, Cloud KMS enables customer-managed encryption keys (CMEK) or customer-supplied encryption keys (CSEK).

**Q40: What is Secret Manager, and why would you use it instead of storing secrets in code?**

A: Secret Manager is a fully managed service for securely storing, versioning, and accessing sensitive values like API keys, database passwords, and certificates. Applications fetch secrets at runtime with IAM-controlled access and audit logging, supporting automatic rotation.

**Q41: How do you ensure data security and compliance in GCP?**

A: Use IAM for least-privilege access with audit logging, encrypt data in transit (TLS) and at rest (Cloud KMS), use Security Command Center for threat detection, keep systems patched, use VPC Service Controls to prevent data exfiltration, and audit against regulatory frameworks.

**Q42: Explain the steps to migrate an existing on-premises application to GCP?**

A: Assess existing architecture and dependencies, plan migration strategy (rehosting, replatforming, refactoring), provision GCP infrastructure (Compute Engine, GKE, App Engine), migrate data using Database Migration Service or Cloud Storage Transfer Service, deploy application, test thoroughly, and optimize.

**Q43: How do you implement CI/CD pipelines in GCP?**

A: Use Google Cloud Build for continuous integration automating testing and packaging, store build artifacts in Cloud Storage or Artifact Registry, use Cloud Deploy or Cloud Run for continuous deployment to GKE/App Engine/Cloud Run, and monitor performance with Cloud Monitor and Logging.

**Q44: What are Managed Instance Groups (MIGs), and how do you use them?**

A: Managed Instance Groups (MIGs) are groups of virtual instances in Google Cloud that are managed as a single entity. They enable autoscaling, ensure high availability across zones, and simplify capacity management during significant workloads.

**Q45: How do you design and manage data pipelines using GCP services?**

A: Determine data flow requirements, use Cloud Storage for data storage, BigQuery for analytics, Google Cloud Dataflow for batch and stream processing, use Cloud Composer for workflow orchestration, implement data governance and security, and monitor performance continuously.

**Q46: Explain how you would handle disaster recovery and backup strategies in GCP?**

A: Replicate critical data across regions using multi-region Cloud Storage and Cloud SQL cross-region replicas, set up automated backups (Persistent Disk snapshots, Cloud SQL backups), deploy compute across regions with global load balancing and health checks, test failover and restoration procedures.

**Q47: What are some common use cases for SSH tunneling in GCP?**

A: Common uses include Secure Remote Access to VMs and databases, Proxying Traffic between local machines and resources, Database Connection to Cloud SQL from development environments, Bypassing Firewalls to access internal resources, and Secure File Transfer using SCP/SFTP.

**Q48: Explain the role of Cloud Armor in protecting applications deployed on GCP?**

A: A safety precaution on the Google Cloud Platform called Cloud Armor protects web apps from Distributed Denial-of-Service (DDoS) attacks and other online risks. It enforces security policies at the network edge, supporting geo-based access controls, IP whitelisting, and blacklisting.

**Q49: What is the difference between Cloud Router and VPN tunnels in GCP?**

A: Cloud Router enables dynamic routing between networks within your Virtual Private Cloud (VPC) and other networks. VPN tunnels provide encrypted internet communications between VPC and on-premises networks, while Cloud Router handles routing within Google Cloud.

**Q50: What are VPC Service Controls, and what problem do they solve?**

A: VPC Service Controls let you create a security perimeter around GCP resources to prevent data from being copied or exfiltrated outside that boundary. This addresses risks where misconfigured settings or compromised credentials could move sensitive data outside the organization.

**Q51: What is Identity-Aware Proxy (IAP), and how does it change how you grant remote access?**

A: Identity-Aware Proxy lets you control access to applications and VMs based on a user's identity and context (device, location) rather than requiring them to be on a VPN. IAP replaces traditional bastion hosts and SSH tunneling by authenticating requests against IAM.

**Q52: What is the difference between GCP, AWS and Azure?**

A: Google Cloud Platform (GCP) emphasizes AI/ML, Big Data, and Kubernetes with strong analytics capabilities. Amazon Web Services (AWS) is the largest cloud provider with the broadest range of services. Microsoft Azure offers strong integration with Windows Server, Active Directory, and Microsoft 365.

**Q53: What is GCP?**

A: Google Cloud Platform is a collection of cloud computing services that Google provides. These services are powered by the same infrastructure as Google's consumer products, including YouTube, Gmail, and other services. Services include Compute, Network, and big data/machine learning processing.

**Q54: Mention some best practices for Cloud Security.**

A: Focus on understanding current state and assessing risk; strategically apply protection based on risk level; adjust cloud access policies as new services emerge; remove malware from cloud services.

**Q55: How is data stored in buckets? What are objects?**

A: Buckets are the basic containers in GCP where the data is stored in objects. Objects are the pieces of data stored inside the buckets.

**Q56: What are the various methods for authentication of Google Compute Engine API?**

A: Using OAuth 2.0, through client libraries, or directly with an access token.

**Q57: What are the advantages of using Compute Engine?**

A: Storage Efficiency, Stability, Easy Integration, Confidential Computing, Security, and compute globally per requirement.

**Q58: Explain what instances are in GCP.**

A: A virtual machine (VM) hosted on Google's network is known as an instance.

**Q59: What is Compute Engine in GCP?**

A: A service enabling creation and operation of virtual machines on Google's infrastructure.

**Q60: What is the default bucket location if I do not specify a location constraint?**

A: The default bucket location is within the US.

**Q61: What happens to disk data when the instance is no longer running?**

A: With persistent disks, data is retained when stopped or restarted. With Local SSD, data cannot be retained if the VM goes down.

**Q62: What is the difference between basic roles and predefined roles?**

A: Basic roles are the legacy Owner, Editor, and Viewer roles. IAM provides predefined roles, which enable more granular access than the basic roles.

**Q63: What is the difference between a project number and a project Id?**

A: Project ID is created automatically; project number is created by user. Project number is mandatory while project ID may be optional for services but required for Compute Engine.

**Q64: What is Google Cloud Storage & Data Services?**

A: GCP delivers storage and database offerings that reduce the burden of building and managing storage infrastructure.

**Q65: Assume you accidentally deleted your instance. Are you going to be able to get it back?**

A: No, instances that have been destroyed once can never be recovered. If it has been stopped, however, it can be restarted.

**Q66: How can we safeguard data during cloud transportation?**

A: GCP has Service Controls that restrict network locations from which users can access data.

**Q67: Which VMs can have a Persistent Disk (PD) attached to them?**

A: VMs in GCE (Compute Engine) and GKE (Kubernetes Engine).

**Q68: What libraries and tools are provided by GCP?**

A: Extensive libraries for Java, Python, Ruby; Google Cloud console; support for XML, API, and JSON API formats.

**Q69: What is the use of MFA?**

A: Multi-factor authentication helps protect user accounts and company data with verification methods such as push notifications, Google Authenticator, and phishing-resistant Titan Security Keys.

**Q70: Is it possible to share data across pipeline instances?**

A: No dataflow-specific mechanism exists; use durable storage like Cloud Storage or an in-memory cache like App Engine.

**Q71: When is HDD the preferred mode of storing data?**

A: HDDs are usually preferred when storing large amounts of data and performing batch operations less sensitive to disk latency.

**Q72: Which NoSQL services does Google offer?**

A: Cloud Datastore, Cloud Firestore, and Cloud Bigtable.

**Q73: What is the function of a Bucket in Google Cloud Storage?**

A: Buckets are the basic containers in GCP where the data is stored in objects. There is no restriction on the number of buckets.

**Q74: Explain how pricing works on Google Cloud?**

A: Charged based on compute instance, network use, and storage. Virtual machines are charged per second with a 1-minute minimum. Storage is charged by data amount; network is charged by data transferred between instances.

**Q75: How can I move servers and virtual machines from another cloud or on-premises to the Google Cloud Platform's Compute Engine?**

A: Use Google Cloud Migrate for Compute Engine to transfer VMs from on-premises, Azure, and AWS at no additional cost.

**Q76: How can a project be made?**

A: Open Google Cloud Platform Console, start a new project or choose an existing one, and set up billing as directed.

**Q77: How would you define "Events and Triggers"?**

A: Events are occurrences in the cloud environment you may respond to. Triggers produce responses to events by declaring interest in specific events.

**Q78: Why do you employ subnets?**

A: Subnets divide an IP network logically into numerous, smaller network pieces, to partition networks and reduce traffic.

**Q79: Do I need to activate Cloud Storage and turn on billing if I was granted access to someone else's bucket?**

A: No; the bucket owner has already set up the project and granted you access.

**Q80: Does cloud storage offer upload and download acceleration features?**

A: Yes. Customers can upload files and download files from cloud storage using a global DNS name. Google transfers data via a private network from the nearest POP with no extra cost.

**Q81: Assume that I have a dedicated team that manages network and firewall rules. How can I maintain this separation of duty?**

A: Grant the Compute Network Admin role to network administrators and the Compute Instance Admin role to developers at the organization/project level.
