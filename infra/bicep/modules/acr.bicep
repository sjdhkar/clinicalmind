// acr.bicep
param name string
param location string
param tags object
param sku string = 'Basic'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: sku }
  properties: { adminUserEnabled: false }
}

output loginServer string = acr.properties.loginServer
output acrId string = acr.id
