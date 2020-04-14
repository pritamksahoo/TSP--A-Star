import pandas as pd
import log_handling as logh


def is_active(pid):
    '''
    Check whether a process is still active
    '''

    filepath = "./server/stable_storage/accounts/accounts.csv"
    accounts = pd.read_csv(filepath)

    record = accounts.loc[accounts['pid'] == pid]

    if record.empty:
        # Wrong PID
        return None
    elif record.at[0, "isActive"] == 'Y':
        # Active
        return True
    else:
        # Logged Out
        return False


def all_active_process():
    '''
    Fetch PID of all active process
    '''

    filepath = "./server/stable_storage/accounts/accounts.csv"
    accounts = pd.read_csv(filepath)

    record = accounts.loc[accounts['isActive'] == 'Y']

    return record["pid"]


def create_account(pid, password, addr):
    '''
    Creates an account with unique pid and password and variable address (hostname and port). Address can change every time client shuts down and restarts again. Throws error if pid already exists
    '''

    filepath = "./server/stable_storage/accounts/accounts.csv"
    accounts = pd.read_csv(filepath)

    hostname, port = addr
    record = accounts.loc[accounts['pid'] == pid]
    # print(record.empty)

    if record.empty:
        active_status = 'N'
        new_record = {
            'pid': pid,
            'password': password,
            'host': hostname,
            'port': port,
            'isActive': active_status
        }

        accounts = accounts.append(new_record, ignore_index=True)

        try:
            # Creating new account
            accounts.to_csv(filepath, index=False, header=True)
            logh.create_new_log_file(pid)

            status = 200
            message = "Account successfully created"

            logh.create_notification(pid, message, 'Y')

        except Exception as e:
            status = 400
            message = "Account creation failed! Server Error! Try again later"

    else:
        status = 400
        message = "Account creation failed! PID already exists"

    data = {
        "status": status,
        "message": message
    }

    return data


def login(pid, password, addr):
    '''
    Log in to a client's acount, address my be different after restart. So, it's need to be updated
    '''

    filepath = "./server/stable_storage/accounts/accounts.csv"
    accounts = pd.read_csv(filepath)

    record = accounts.loc[(accounts['pid'] == pid) & (accounts['password'] == password)]
    # print(record["isActive"].to_list())

    if not record.empty and record["isActive"].to_list()[0] == 'Y':
        status = 400
        message = "Login Failed! Already running in another window"

    elif not record.empty:
        hostname, port = addr

        # Updating address
        index = accounts.index[(accounts['pid'] == pid) & (accounts['password'] == password)].tolist()[0]
        accounts.at[index, 'host'] = hostname
        accounts.at[index, 'port'] = port
        accounts.at[index, 'isActive'] = 'Y'
        accounts.to_csv(filepath, index=False, header=True)

        status = 200
        message = "You are logged in"
        
        logh.create_notification(pid, message, 'Y')

    else:
        status = 400
        message = "Login Failed! Wrong PID or PASSWORD"

    data = {
        "status": status,
        "message": message
    }

    return data    



if __name__ == '__main__':
    # print(login("abcde", "pass", ['127.0.0.1', 8800]))
    logh.create_new_log("abcde", {"from": "a", "to": "b", "amount": 100})