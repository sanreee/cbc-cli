from collections import OrderedDict

menu_main = OrderedDict([
    ('General','menu_general'),
    ('Discovery','menu_discovery'),
    ('Execution','menu_execution'),
    ('Persistence','menu_persistence'),
    ('Credential Access','menu_creds'),
    ('Lateral Movement','menu_lateral'),
    ('Defense evasion','menu_evasion'),
    ('Powershell','menu_powershell'),
    ('Emotet','menu_emotet'),
    ('LOLBINS','menu_lolbins'),
    ('Free search','free_search'),
    ('Toggle sweep mode (all instances or only the current)','toggle_sweep')
])

menu_general = OrderedDict([
    ('Back','back'),
    ('Qakbot - Excel spawn rundll32 - https://pastebin.com/7Ms8hSnd',
        'process_name:rundll32.exe process_cmdline:dllregisterserver parent_name:excel.exe'),
])

menu_execution = OrderedDict([
    ('Back','back'),

])

menu_powershell = OrderedDict([
    ('Back','back'),
    ('T1086 - Powershell remote IEX/DownloadString', 
        'process_name:powershell.exe AND (process_cmdline:downloadstring OR process_cmdline:iex) -process_cmdline:UTF8.GetString -process_cmdline:choco -process_cmdline:computeMetadata'),
])

menu_emotet = OrderedDict([
    ('Back','back'),

])

menu_discovery = OrderedDict([
    ('Back','back'),

])

menu_creds = OrderedDict([
    ('Back','back'),

])

menu_lateral = OrderedDict([
    ('Back','back'),

])

menu_evasion = OrderedDict([
    ('Back','back'),

])

menu_persistence = OrderedDict([
    ('Back','back'),
    
])

menu_lolbins = OrderedDict([
    ('Back','back'),

])