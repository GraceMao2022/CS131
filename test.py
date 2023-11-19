class Potato:
    def __init__(self, x):
        self.weight = x
        self.bites = []

    def bitten_by(self, name):
        self.weight -= 1
        self.bites = self.bites + [name]
        return self.bites
def foo(potat):
    names = potat.bitten_by("Cui")
    names = names + ["Andrey"]

def main():
    p1 = Potato(5)

    names = p1.bitten_by("Liu")

    names.append("Carey")
    print(p1.bites) #[Liu, Carey]

    p1.bitten_by("Brian")
    print(p1.bites) #[Liu, Carey, Brian]
    print(names) #[Liu, Carey]

    foo(p1) 
    print(p1.bites) #[Liu, Carey, Brain, Cui]
    print(names) #[Liu, Carey]

if __name__ == "__main__":
    main()