"""Home the capper machine."""

from qubot_drivers.machines.capper import Capper


def main():
    capper = Capper(qubot_ip="192.168.2.113")
    capper.home()
    capper.pick_cap_from(x=7, y=-62, z=-78.5)
    capper.cap()
    capper.decap()
    capper.place_cap_at(x=7, y=-62, z=-78.5)


if __name__ == "__main__":
    main()
