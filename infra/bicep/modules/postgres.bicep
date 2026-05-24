// postgres.bicep
param name string
param location string
param tags object
param adminPassword string
@secure()
param sku string = 'Standard_B1ms'
param storageSizeGB int = 32

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: { name: sku, tier: sku == 'Standard_B1ms' ? 'Burstable' : 'GeneralPurpose' }
  properties: {
    administratorLogin: 'clinicalmind'
    administratorLoginPassword: adminPassword
    version: '16'
    storage: { storageSizeGB: storageSizeGB }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

// pgvector extension
resource pgvectorExtension 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-12-01-preview' = {
  parent: postgres
  name: 'azure.extensions'
  properties: { value: 'vector,pg_trgm,uuid-ossp' }
}

output host string = postgres.properties.fullyQualifiedDomainName
output serverId string = postgres.id
