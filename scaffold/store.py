from dataclasses import dataclass
import os


@dataclass
class Dependency:
    key: str
    cflags: str = ""
    ldflags: str = ""


class Store:
    STORE_DIR = "store"
    INTERNAL_DIR = ".internal"

    def __init__(self):
        self.registry: list[Dependency] = []

    def _validate_pkg(self, pkg) -> bool:
        # TODO: implement
        return True

    def load(self):
        tree = list(os.walk(self.STORE_DIR))
        pkgs = [pkg for pkg in tree[0][1] if pkg != self.INTERNAL_DIR]

        for pkg in pkgs:
            if not self._validate_pkg(pkg):
                print("ERRO: invalid package 'pkg'")
                continue
            self.registry.append(Dependency(
                key=pkg
            ))

if __name__ == "__main__":
    store = Store()
    store.load()
    print(store.registry)
