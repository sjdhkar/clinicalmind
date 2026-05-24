// AKS module — Kubernetes cluster with optional GPU node pool for HF inference
param name string
param location string
param tags object
param nodeCount int = 1
param nodeVmSize string = 'Standard_D4s_v3'
param enableGpuNodePool bool = false
param acrId string

resource aks 'Microsoft.ContainerService/managedClusters@2024-06-01' = {
  name: name
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    dnsPrefix: name
    enableRBAC: true
    agentPoolProfiles: [
      {
        name: 'system'
        count: nodeCount
        vmSize: nodeVmSize
        mode: 'System'
        osDiskSizeGB: 128
        enableAutoScaling: true
        minCount: 1
        maxCount: nodeCount + 2
      }
    ]
    networkProfile: { networkPlugin: 'azure' }
    oidcIssuerProfile: { enabled: true }   // for workload identity
    securityProfile: {
      workloadIdentity: { enabled: true }
    }
  }
}

// GPU node pool for HuggingFace inference (prod only)
resource gpuNodePool 'Microsoft.ContainerService/managedClusters/agentPools@2024-06-01' = if (enableGpuNodePool) {
  parent: aks
  name: 'gpu'
  properties: {
    count: 1
    vmSize: 'Standard_NC6s_v3'   // NVIDIA V100 16GB
    mode: 'User'
    nodeTaints: ['nvidia.com/gpu=true:NoSchedule']
    nodeLabels: { 'workload-type': 'hf-inference' }
    enableAutoScaling: false   // GPU nodes are expensive — no autoscaling
  }
}

// Attach ACR to AKS so it can pull images without explicit auth
resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, acrId, 'AcrPull')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: aks.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

output aksName string = aks.name
output aksId string = aks.id
output kubeletIdentityObjectId string = aks.properties.identityProfile.kubeletidentity.objectId
