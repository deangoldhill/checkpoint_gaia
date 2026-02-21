# Check Point Gaia Home Assistant Integration

Full integration for Check Point Gaia firewalls (R80.40 / R81 / R82) using the official GAIA REST API.

## Sensors
- CPU Usage (%)
- Memory Usage (%)
- Active Sessions
- Sessions per Second
- Total Current Throughput (Mbps)
- VPN Status (Up/Down)
- Uptime
- Version
- Content Updates Package Version
- Serial Number
- Number of Routes
- Interfaces (count + full details in attributes)

## HACS Installation
1. HACS → Integrations → ⋮ → **Custom repositories**
2. Repository: `https://github.com/YOUR_GITHUB_USERNAME/checkpoint-gaia`
3. Category: **Integration**
4. Add → Search "Check Point Gaia" → Install
5. Restart Home Assistant
6. Settings → Devices & Services → + Add Integration → **Check Point Gaia**

**Firewall requirement (one-time)**
```bash
gaia_api access --user YOUR_API_USER --enable true
gaia_api restart
