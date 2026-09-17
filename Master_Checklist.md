# APEX BRIDGE PROPERTIES - MASTER INFRASTRUCTURE CHECKLIST
## Last Updated: September 2026

*Rule: This master checklist tracks all infrastructure and operational tasks (Items 1–6). Whenever an item is completed, it is removed from this list. Whenever the user asks what can be done next, refer to the remaining items on this list.*

### Active Priority Items (Executing Now)
1. **Live HLR Phone Verification:**
   - Integrate and execute live carrier network validation (e.g., via AbstractAPI / Twilio Lookup) to identify active vs. disconnected phone numbers.
2. **Inbound Business Call Forwarding:**
   - Configure Twilio routing on `+1 (816) 666-9735` to forward all incoming calls directly to personal mobile `+1 (864) 913-9408`.
3. **Outbound Business Caller ID Masking:**
   - Configure mobile calling/dialer integration so calls placed from personal mobile devices display the official business caller ID (`+1 (816) 666-9735`).

### Deferred Items (Post-Closing Upgrades)
4. **Dedicated Always-On Desktop Computer:**
   - Set up a dedicated machine running 24/7 as the permanent local Command Center and sync hub.
5. **Personal Storage / NAS Server:**
   - Set up local network storage (NAS) for automated daily physical backups of all databases and records.
6. **PostgreSQL Cloud Database Migration:**
   - Migrate web backend from SQLite to permanent cloud PostgreSQL (Render/Supabase) to eliminate ephemeral disk sync overhead.

