###############################################################################
# Copyright 2019 StarkWare Industries Ltd.                                    #
#                                                                             #
# Licensed under the Apache License, Version 2.0 (the 'License').             #
# You may not use this file except in compliance with the License.            #
# You may obtain a copy of the License at                                     #
#                                                                             #
# https://www.starkware.co/open-source-license/                               #
#                                                                             #
# Unless required by applicable law or agreed to in writing,                  #
# software distributed under the License is distributed on an 'AS IS' BASIS,  #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    #
# See the License for the specific language governing permissions             #
# and limitations under the License.                                          #
###############################################################################


from .balances_to_merkle_root import balances_to_merkle_root


def test_balances_to_merkle_root():

    balances_data = {'tree_height': 31}
    balances_data['vaults_data'] = []
    balances_data['vaults_data'].append({
        'vault_id': 1,
        'amount': '200',
        'stark_key': '2150471919205542344617760747371611320347608032404155555365727419344817674468',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 10,
        'amount': '0',
        'stark_key': '539829086518955806802559665210396590895487630747645305183222664344785245366',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 2,
        'amount': '1100',
        'stark_key': '255827121414984984902289315001765951701282438658483627788136436631032988774',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 3,
        'amount': '1000',
        'stark_key': '304941497186797564249797438768757617063341886380757948160471033432136820085',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 4,
        'amount': '0',
        'stark_key': '405153257691983371752259838423620212071917624006438153396220869063399643595',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 5,
        'amount': '0',
        'stark_key': '2167047720162313965884216566332774481993123987533500880835565588081197632956',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 6,
        'amount': '0',
        'stark_key': '2694279210121066307397013436414076515028028887698365169968720618785611482135',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 7,
        'amount': '0',
        'stark_key': '860551529424057386839772719726463935477633086527131035031575372182075024768',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 8,
        'amount': '0',
        'stark_key': '1775631505764171291499621242982197589316934794861071304378556839875707501744',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    balances_data['vaults_data'].append({
        'vault_id': 9,
        'amount': '0',
        'stark_key': '1232873086413625719944406979550653950452854334079699132669304355721634644592',
        'token_id': '836064248892964870389495188378837350478052431396515437913195311707854996139'
    })
    assert balances_to_merkle_root(balances_data, 1) == \
        3375325109498442223145574558741161874332627861616082756775988473812918344480
