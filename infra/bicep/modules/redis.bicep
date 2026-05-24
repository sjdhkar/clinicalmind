// redis.bicep
param name string
param location string
param tags object
param sku string = 'Basic'
param capacity int = 0

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: { name: sku, family: sku == 'Premium' ? 'P' : 'C', capacity: capacity }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: { 'maxmemory-policy': 'volatile-lru' }
  }
}

output host string = redis.properties.hostName
output redisId string = redis.id
