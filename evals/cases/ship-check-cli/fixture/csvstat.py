import argparse
import csv
import sys


def read_rows(path, delimiter):
    with open(path, newline="") as handle:
        header = handle.readline().strip().split(",")
        reader = csv.reader(handle, delimiter=delimiter)
        return header, [row for row in reader if row]


def summarize(header, rows, column):
    index = header.index(column)
    values = [float(row[index]) for row in rows]
    total = sum(values)
    return {
        "count": len(values),
        "mean": total / len(values),
        "share_of_max": max(values) / total,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="csvstat")
    parser.add_argument("path")
    parser.add_argument("column")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--percent", action="store_true", help="show share_of_max as a percentage")
    args = parser.parse_args(argv)
    header, rows = read_rows(args.path, args.delimiter)
    result = summarize(header, rows, args.column)
    share = result["share_of_max"]
    shown = f"{round(share, 2)}%" if args.percent else f"{share:.2f}"
    print(f"count={result['count']} mean={result['mean']:.2f} share_of_max={shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
