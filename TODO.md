# Issues & TODOs

## TODO
- [ ] Add General tests 😱
- [ ] Add 'strict' mode that only works with 100% compliant IdP implementations of SCIM
- [ ] Add options around which fields are used to resolve manager/group member fields (i.e. for Okta as SCIM ID is not used)
- [ ] Add UI to manage tenants, apps, API keys, and show data
- [ ] Review API key implementation and storage
- [ ] Tenant-wide SCIM read tokens (for integrations/identity data aggregation)

## To Test
- [ ] Test untested fields: x509, entitlements, roles, photos, ims, password
- [ ] Test tenants more broadly

## To Fix
- [ ] There are some quirks with the manager display name currently and manager resolution.

## Not Currently Supported
- [ ] Nested groups / indirect memberships (type=indirect) are not currently supported.
- [ ] Bulk operations are not currently supported.

Also, section on how to test using Ngrok / testing in general.