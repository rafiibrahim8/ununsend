import re
from urllib.parse import unquote

x = 'https://l.facebook.com/l.php?u=https%3A%2F%2Fcdn.fbsbx.com%2Fv%2Ft59.2708-21%2F267701312_764035478319437_5017017823950929320_n.pdf%2F1.pdf%3F_nc_cat%3D108%26ccb%3D1-5%26_nc_sid%3D0cab14%26_nc_eui2%3DAeGC1Q027Ox3aEPiQ7AmLIcXQc6q--WZGMZBzqr75ZkYxpdCZl6Xxs5_dSiCeowUs9sNS6MlAtQqi352tt-NZpt_%26_nc_ohc%3DRiqBA5oAy2IAX_AqvJ2%26_nc_ht%3Dcdn.fbsbx.com%26oh%3D03_AVL7REVDdFoz6OU23m-9JVvXrlwYtq1C7oyCO-DnUC2PAw%26oe%3D61C7810A%26dl%3D1&h=AT1Z-VXxCuVRfhZ7ZjBr-a6vjzs3Z3TXQrPSkN_cWabhSS_Yo1YQAhqfY1PEuOyfkoscNClOyZ32Ko92yiJC_CclatuhoI9envHIDBlPepFUm4Aa7SRzxd2q-ug6tiB-8JoXHwsP0rJ5NvRX6TqyHVOv2_4&s=1'
#x = 'https://l.facebook.com/l.php?u=https%3A%2F%2Fyoutu.be%2FY1doS51Ec4I&h=AT2t3jhcCC8aMHL54jCfaAvdc2ABwHSiIxW-JU-XzU3V9Jfv13LP7II6fD53IbwDHF2B8hFhS8sl3GCAz_tj_Jlg1cHn-kGXOvyboVvuTeBsqianb1riMy9Y2eLNlvQiZyg2DrbkmeuOZig&s=1'

def get_file_name(url):
    FILE_NAME_REGEX = r'(?<=\/)[^\/\?#]+(?=[^\/]*$)' # Copied from: https://stackoverflow.com/a/56258202/13205702 
    start = url.index('u=h') + 2
    url = unquote(url[start:])
    if re.findall(r'([0-9]{15}_n\.[a-z]*)', url):
        return re.findall(FILE_NAME_REGEX, url)[0], True
    return url, False


print(get_file_name(x))



# print(x.find('u=http'))
# print(x.find('&', 29+2))

# print(x[29+2:426])
