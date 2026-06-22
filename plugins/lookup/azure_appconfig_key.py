# Copyright (c) 2022 Hai Cao, <t-haicao@microsoft.com>, Marcin Slowikowski (@msl0)
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
---
name: azure_keyvault_secret
author:
    - Wouter Stinkens (@wstinkens)
version_added: '3.20.0'
requirements:
    - azure
short_description: Read key from Azure App Configuration.
description:
  - This lookup returns the content of key saved in Azure App Configuration.
  - When ansible host is MSI enabled Azure VM, user don't need provide any credential to access to Azure App Configuration.
options:
    _terms:
        description: Key name to lookup.
        required: True
    label_filter:
        description: Filter key by label
        required: True
    tag_filters:
        description: Filter key by tags, in format of key1=value1,key2=value2
    app_config_endpoint:
        description: Endpoint of Azure App Configuration.
        required: True
    client_id:
        aliases:
        - azure_client_id
    secret:
        aliases:
        - azure_secret
    tenant:
        aliases:
        - azure_tenant
    cloud_environment:
        aliases:
        - azure_cloud_environment
    use_cli:
        description:
          - When I(use_cli=True), get the 'az login' credential authentication, default if false.
          - Deprecated, please use I(auth_source=cli) instead.
notes:
    - If MSI is not enabled on ansible host, it's required to provide a valid service principal which has access to the key vault.
    - To authenticate via service principal, pass client_id, secret and tenant or set environment variables
      AZURE_CLIENT_ID, AZURE_CLIENT_SECRET and AZURE_TENANT_ID.
    - Authentication via C(az login) is also supported.

extends_documentation_fragment:
    - azure.azcollection.azure_plugin
"""

EXAMPLE = """
- name: Look up key when azure cli login
  debug:
    msg: msg: "{{ lookup('azure.azcollection.azure_appconfig_key', 'keyName', label_filter='labelValue', app_config_endpoint=app_config_endpoint, auth_source='cli')}}"

"""

RETURN = """
  _raw:
    description: secret content string
"""

from ansible_collections.azure.azcollection.plugins.module_utils.azure_rm_common import AzureRMAuth
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
try:
    import logging
    from azure.appconfiguration.provider import (
        load,
        SettingSelector,
        AzureAppConfigurationKeyVaultOptions
    )

except ImportError:
    pass

display = Display()

TOKEN_ACQUIRED = False

logger = logging.getLogger("azure.identity").setLevel(logging.ERROR)


class LookupModule(LookupBase):
    def run(self, terms, variables, **kwargs):

        self.set_options(var_options=variables, direct=kwargs)

        ret = []

        app_config_endpoint = self.get_option('app_config_endpoint')
        label_filter = self.get_option('label_filter')
        tag_filters = self.get_option('tag_filters')

        auth_source = self.get_option('auth_source')
        client_id = self.get_option('client_id')
        secret = self.get_option('secret')
        tenant = self.get_option('tenant')

        # Legacy use_cli will set auth_source to cli.
        if self.get_option('use_cli'):
            auth_source = 'cli'
        
        # If auth_source is auto but no client_id or secret passed in switch to cli
        if auth_source == 'auto':
            if any(v is None for v in [client_id, secret, tenant]):
                auth_source = 'cli'

        auth_options = dict(
            auth_source=auth_source,
            client_id=client_id,
            secret=secret,
            tenant=tenant,
            is_ad_resource=True
        )

        azure_auth = AzureRMAuth(**auth_options)

        key_vault_options = AzureAppConfigurationKeyVaultOptions(credential=azure_auth.azure_credential_track2)

        ret = []
        for term in terms:
            try:
                if tag_filters:
                    selects = {SettingSelector(key_filter=term, label_filter=label_filter, tag_filters=tag_filters)}
                else:
                    selects = {SettingSelector(key_filter=term, label_filter=label_filter)}
                config = load(endpoint=app_config_endpoint, credential=azure_auth.azure_credential_track2, selects=selects, key_vault_options=key_vault_options)

                ret.append(config.values())
            except Exception:
                raise AnsibleError('Failed to fetch key ' + term + ' with label ' + str(label_filter) + ' from ' + app_config_endpoint + '.')
        return ret

