class ListHelper:
    @staticmethod
    def flatten(array):
        return [
            x
            for xs in array if xs
            for x in xs if x
        ]

    @staticmethod
    def partition(pred, iterable):
        trues = []
        falses = []
        for item in iterable:
            if pred(item):
                trues.append(item)
            else:
                falses.append(item)
        return trues, falses

