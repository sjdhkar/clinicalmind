// ============================================================
// ClinicalMind — Azure Infrastructure as Code
// Deploys: AKS, PostgreSQL Flexible Server, Redis Cache,
//          Container Registry, Key Vault, Service Bus
//
// Usage:
//   az deployment sub create \
//     --location uksouth \
//     --template-file infra/bicep/main.bicep \
//     --parameters @infra/bicep/params.dev.json
// ============================================================

targetScope = 'subscription'

@description('Environment name (dev/staging/prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure region')
param location string = 'uksouth'

@description('PostgreSQL admin password')
@secure()
param postgresAdminPassword string

var prefix = 'cm-${environment}'
var tags = {
  project: 'ClinicalMind'
  environment: environment
  managedBy: 'bicep'
}

// ── Resource Group ────────────────────────────────────────────
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'rg-${prefix}'
  location: location
  tags: tags
}

// ── Container Registry ────────────────────────────────────────
module acr 'modules/acr.bicep' = {
  name: 'acr-deploy'
  scope: rg
  params: {
    name: replace('acr${prefix}', '-', '')
    location: location
    tags: tags
    sku: environment == 'prod' ? 'Premium' : 'Basic'
  }
}

// ── Key Vault ─────────────────────────────────────────────────
module kv 'modules/keyvault.bicep' = {
  name: 'kv-deploy'
  scope: rg
  params: {
    name: 'kv-${prefix}'
    location: location
    tags: tags
  }
}

// ── PostgreSQL Flexible Server ────────────────────────────────
module postgres 'modules/postgres.bicep' = {
  name: 'postgres-deploy'
  scope: rg
  params: {
    name: 'psql-${prefix}'
    location: location
    tags: tags
    adminPassword: postgresAdminPassword
    sku: environment == 'prod' ? 'Standard_D2s_v3' : 'Standard_B1ms'
    storageSizeGB: environment == 'prod' ? 128 : 32
  }
}

// ── Redis Cache ───────────────────────────────────────────────
module redis 'modules/redis.bicep' = {
  name: 'redis-deploy'
  scope: rg
  params: {
    name: 'redis-${prefix}'
    location: location
    tags: tags
    sku: environment == 'prod' ? 'Standard' : 'Basic'
    capacity: environment == 'prod' ? 1 : 0
  }
}

// ── Service Bus ───────────────────────────────────────────────
module serviceBus 'modules/servicebus.bicep' = {
  name: 'sb-deploy'
  scope: rg
  params: {
    name: 'sb-${prefix}'
    location: location
    tags: tags
  }
}

// ── AKS Cluster ───────────────────────────────────────────────
module aks 'modules/aks.bicep' = {
  name: 'aks-deploy'
  scope: rg
  params: {
    name: 'aks-${prefix}'
    location: location
    tags: tags
    nodeCount: environment == 'prod' ? 3 : 1
    nodeVmSize: environment == 'prod' ? 'Standard_D4s_v3' : 'Standard_B2s'
    enableGpuNodePool: environment == 'prod'
    acrId: acr.outputs.acrId
  }
}

// ── Outputs ───────────────────────────────────────────────────
output aksName string = aks.outputs.aksName
output acrLoginServer string = acr.outputs.loginServer
output postgresHost string = postgres.outputs.host
output redisHost string = redis.outputs.host
output resourceGroupName string = rg.name
