# Exchange Certificate Integration

## Overview

The JML Automation system integrates with Exchange Online using certificate-based authentication for unattended automation. The certificate and credentials are securely stored in 1Password and retrieved at runtime.

## 1Password Structure

### Microsoft Graph API Credentials (`microsoft-graph-api`)
- **Location**: `op://IT/microsoft-graph-api`
- **Fields**:
  - `username`: Application (Client) ID
  - `password`: Application Secret
  - `tenant_id`: Azure Tenant ID
  - `certificate_thumbprint`: Exchange certificate thumbprint

### Exchange Certificate File (`ExchangeOnline_Cert`)
- **Location**: `op://IT/ExchangeOnline_Cert`
- **File**: `ExchangeOnline-Cert.cer`
- **Purpose**: Certificate file for Exchange Online authentication

## Configuration Integration

The system automatically:

1. **Retrieves credentials** from `microsoft-graph-api` item in 1Password
2. **Downloads certificate** from `ExchangeOnline_Cert` item to `docs/certs/` directory
3. **Gets certificate thumbprint** from the `certificate_thumbprint` field
4. **Uses certificate-based authentication** for Exchange Online PowerShell commands

## Code Usage

```python
from jml_automation.config import Config
from jml_automation.services.microsoft import MicrosoftTermination

# Initialize configuration
config = Config()

# Get certificate thumbprint
thumbprint = config.get_exchange_certificate_thumbprint()

# Initialize Microsoft service (automatically uses certificate)
ms_service = MicrosoftTermination()

# Certificate is automatically used in Exchange operations
ms_service.convert_mailbox_to_shared("user@company.com")
ms_service.delegate_mailbox_access("user@company.com", "manager@company.com")
```

## Security Features

- ✅ **Certificate stored in 1Password**: Not in source code or local files
- ✅ **Automatic retrieval**: Downloaded only when needed
- ✅ **Local caching**: Certificate cached locally in `docs/certs/` (gitignored)
- ✅ **Thumbprint caching**: Thumbprint cached in memory to avoid repeated 1Password calls
- ✅ **Windows Certificate Store**: Certificate installed to user's personal store for PowerShell access

## Maintenance

### Updating Certificate
1. Upload new certificate to 1Password: `op://IT/ExchangeOnline_Cert`
2. Update thumbprint in `microsoft-graph-api` item
3. System will automatically use new certificate on next run

### Troubleshooting
- Check certificate is installed: `certutil -user -store My`
- Verify 1Password access: `op item get microsoft-graph-api --vault IT`
- Check certificate file: `ls docs/certs/exchange_online.cer`

## Certificate Details

- **Subject**: `CN=TerminationAutomation-ExchangeOnline`
- **Thumbprint**: `df8b5fa21923e56aba0fc540cbc2056977999cf9`
- **Validity**: August 5, 2025 - August 5, 2026
- **Store Location**: Current User Personal Store (`Cert:\CurrentUser\My`)
