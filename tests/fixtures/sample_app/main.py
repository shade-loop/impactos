from sample_app.service import UserService

def run():
    svc = UserService()
    print(svc.get_user("alice"))

if __name__ == "__main__":
    run()
