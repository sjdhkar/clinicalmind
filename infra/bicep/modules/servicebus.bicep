// servicebus.bicep
param name string
param location string
param tags object

resource sb 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'Standard', tier: 'Standard' }
}

// Observation events queue (triggers AI pipeline on new observations)
resource observationQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: sb
  name: 'observation-events'
  properties: {
    maxDeliveryCount: 3
    lockDuration: 'PT1M'
    defaultMessageTimeToLive: 'PT1H'
  }
}

output serviceBusEndpoint string = sb.properties.serviceBusEndpoint
output sbId string = sb.id
