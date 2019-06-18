from types import SimpleNamespace
from copy import deepcopy

from jinja2 import Environment, FileSystemLoader
import yaml

env = Environment(loader=FileSystemLoader('param_data'),
                  trim_blocks=True,
                  lstrip_blocks=True)

# Load the nc params data
with open('param_data/axis_nc.yaml', 'r') as fd:
    data = yaml.safe_load(fd)
nc_params = []
for param, info in data.items():
    ns = SimpleNamespace(
        stConfig=param,
        MC_AxisParameter=info['mc'],
        is_bool=(info['type'] == 'bool'))
    camelcase = ''.join(txt.capitalize() for txt in param.split('_'))
    ns.fb_write = 'fbWrite' + camelcase
    ns.fb_write_done = ns.fb_write + '.Done'
    ns.fb_write_busy = ns.fb_write + '.Busy'
    ns.fb_write_error = ns.fb_write + '.Error'
    ns.fb_read = 'fbRead' + camelcase
    ns.fb_read_valid = ns.fb_read + '.Valid'
    ns.fb_read_busy = ns.fb_read + '.Busy'
    ns.fb_read_error = ns.fb_read + '.Error'
    nc_params.append(ns)

# Make the axis write nc file
template = env.get_template('FB_AxisWriteNC.TcPOU')
stream = template.stream(nc_params=nc_params)
stream.dump('FB_AxisWriteNC.TcPOU')

# Make the axis read nc file
template = env.get_template('FB_AxisReadNC.TcPOU')
stream = template.stream(nc_params=nc_params)
stream.dump('FB_AxisReadNC.TcPOU')

# Load the CoE params data
terms = ['5042', '70x1']
coe_params_dict = {}
for term in terms:
    with open(f'param_data/{term}_coe.yaml', 'r') as fd:
        data = yaml.safe_load(fd)
    coe_params = []
    for param, info in data.items():
        ns = SimpleNamespace(stConfig=param)
        ns.title = ''.join(txt.capitalize() for txt in param.split('_'))
        ns.nindex = 'nInd' + ns.title
        ns.multi_channel = isinstance(info['index'], list)
        if ns.multi_channel:
            ns.subindex = info['index'][0].split(':')[1]
            ns.index = [ind.split(':')[0] for ind in info['index']]
        else:
            ns.index, ns.subindex = info['index'].split(':')
        coe_params.append(ns)
    coe_params_dict[term] = coe_params

# Find and edit the existing files
# Template is partial, we fill in an existing file's structure
template = env.get_template('FB_AxisCoE.template')
for term in terms:
    for mode in ('read', 'write'):
        filename = f'FB_Axis{mode.capitalize()}{term}.TcPOU'
        with open(filename, 'r') as fd:
            lines = fd.readlines()
        # split file into before and after the target lines
        before = []
        overwrite = []
        after = []
        curr = before
        for line in lines:
            curr.append(line)
            if '<Declaration>' in line:
                curr = overwrite
            if '</Implementation>' in line:
                curr = after
        # update the coe params with read/write info
        coe_params = deepcopy(coe_params_dict[term])
        for ns in coe_params:
            camelcase = ''.join(txt.capitalize() for txt in param.split('_'))
            ns.fb_name = f'fb{mode.capitalize()}{ns.title}'
            ns.fb_busy = ns.fb_name + '.bBusy'
            ns.fb_error = ns.fb_name + '.bError'
            ns.fb_ads_err_id = ns.fb_name + '.iAdsErrId'
            ns.fb_can_err_id = ns.fb_name + '.iCANopenErrId'
        # use the template
        stream = template.stream(coe_params=coe_params,
                                 read=(mode == 'read'),
                                 write=(mode == 'write'))
        new = list(stream)
        # drop the byte order mark U+FEFF
        new[0] = new[0][1:]
        # write the new file
        with open(filename, 'w') as fd:
            fd.writelines(before + new + after)
