#!/usr/bin/env python
'''
python3 script
plotting code for generate realtime metareasoning related plots

Author: Tianyi Gu
Date: 04/21/2021
'''

__author__ = 'TianyiGu'

import argparse
import json
import os
# import sys
from datetime import datetime
import re
# import math
from json.decoder import JSONDecodeError
import sys

from scipy.stats import gmean

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pandas.plotting import table
import numpy as np

from plotConfig import Configure

def parseArugments():

    parser = argparse.ArgumentParser(description='boundedCostPlot')

    parser.add_argument(
        '-d',
        action='store',
        dest='domain',
        help='domain: tile(default), pancake, racetrack, vacuumworld',
        default='tile')

    parser.add_argument(
        '-s',
        action='store',
        dest='subdomain',
        help='subdomain: tile: uniform(default), heavy, inverse; \
        pancake: regular, heavy; \
        racetrack : barto-big,uniform-small, barto-bigger, hanse-bigger-double;\
        vacuumworld: uniform, heavy',
        default='uniform')

    parser.add_argument(
        '-b',
        action='store',
        dest='lookaheadStart',
        help='lookahead start: eg anything above 3,(default: 3)',
        default='3')

    parser.add_argument(
        '-e',
        action='store',
        dest='lookaheadEnd',
        help='lookahead end: anything below 100, (default: 100)',
        default='100')

    parser.add_argument('-z',
                        action='store',
                        dest='size',
                        help='domain size (default: 4)',
                        default='4')

    parser.add_argument(
        '-t',
        action='store',
        dest='plotType',
        help='plot type, nodeGen(default), cpu, coveragetb, coverageplt, \
                         nodeGenDiff, fixedbaseline, part10',
        default='nodeGen')

    parser.add_argument(
        '-ht',
        action='store',
        dest='heuristicType',
        help='heuristic type: racetrack:euclidean(default), dijkstra, \
              gap, gapm1, gapm2',
        default='euclidean')

    parser.add_argument(
        '-ot',
        action='store',
        dest='outTime',
        help='time in outfile name (default NA, use now())',
        default='NA')

    parser.add_argument(
        '-os',
        action='store',
        dest='outSuffix',
        help='suffix in outfile name (default NA)',
        default='NA')

    parser.add_argument(
        '-r',
        action='append',
        dest='removeAlgorithm',
        help='remove (omit) algorithm (default NA)',
        default=[])

    return parser

#_ = totalInstance


def makeLinePlot(xAxis, yAxis, dataframe, hue,
                 xLabel, yLabel, _totalInstance,
                 outputName, colorDict, title,
                 showSolvedInstance=True, useLogScale=True):
    sns.set(rc={
        'figure.figsize': (13, 10),
        'font.size': 27,
        'text.color': 'black',
    })
    plt.rcParams["font.family"] = 'serif'
    plt.rcParams["font.serif"] = ['Times New Roman']

    # mean_df = dataframe.groupby(hue).mean().reset_index()
    mean_df = dataframe.groupby(hue)[yAxis].apply(gmean).reset_index()
    mean_df = mean_df.sort_values(by=[yAxis], ascending=False)
    hue_order_list = mean_df[hue]

    ax = sns.lineplot(x=xAxis,
                      y=yAxis,
                      hue=hue,
                      hue_order=hue_order_list,
                      style=hue,
                      palette=colorDict,
                      data=dataframe,
                      err_style="bars",
                      # estimator=gmean,
                      # ci=None,
                      dashes=False
                      )

    ax.tick_params(colors='black', labelsize=24)

    if showSolvedInstance:
        ax.legend().texts[0].set_text(
            'Solved:' + str(len(dataframe['instance'].unique())))
    if useLogScale:
        ax.set_yscale("log")

    # ax.set_xscale("log")
    # ax.set_xticks(dataframe[xAxis].tolist())
    # ax.set_xticklabels(dataframe[xAxis].tolist())

    fontSize = 36
    ax.set_title(title, fontdict={'fontsize': fontSize})

    # plt.ylabel('')
    # plt.xlabel('')
    plt.ylabel(yLabel, color='black', fontsize=fontSize)
    plt.xlabel(xLabel, color='black', fontsize=fontSize)
    plt.setp(ax.get_legend().get_texts(), fontsize='26')  # for legend text
    plt.setp(ax.get_legend().get_title(), fontsize='26')  # for legend title

    plt.savefig(outputName, bbox_inches="tight", pad_inches=0)
    plt.savefig(outputName.replace(".jpg", ".eps"),
                bbox_inches="tight", pad_inches=0)
    plt.close()
    plt.clf()
    plt.cla()


def makePairWiseDf(rawdf, baseline, algorithms):
    df = pd.DataFrame()
    df["Algorithm"] = np.nan
    df["instance"] = np.nan
    df["boundValues"] = np.nan
    df["nodeGen"] = np.nan
    df["nodeExp"] = np.nan
    df["cpu"] = np.nan

    BaselineDf = rawdf[rawdf["Algorithm"] == baseline]

    # print("baseline data count, ", len(BaselineDf))

    for instance in BaselineDf["instance"].unique():
        dfins = rawdf[rawdf["instance"] == instance]
        # keep instances solved by all algorithms across all bounds
        if len(dfins) == len(algorithms) * len(BaselineDf["boundValues"].unique()):
            df = df.append(dfins)

    # for instance in BaselineDf["instance"].unique():
        # for boundP in BaselineDf["boundValues"].unique():
            # # print(instance, boundP)
            # dfins = rawdf[(rawdf["instance"] == instance) &
            # (rawdf["boundValues"] == boundP)]
            # if len(dfins) == len(algorithms):  # keep instances solved by all algorithms
            # df = df.append(dfins)

    boundPercents = BaselineDf["boundValues"].unique()
    boundPercents.sort()
    for boundP in boundPercents:
        print("bound percent ", boundP, "valid instances: ", len(
            df[df["boundValues"] == boundP]["instance"].unique()), "baseline avg:",
            df[(df["boundValues"] == boundP) &
               (df["Algorithm"] == baseline)]["nodeGen"].mean())

    differenceNodeGen = []

    for rowdata in df.iterrows():
        row = rowdata[1]
        relateastar = df[(df["instance"] == row['instance']) &
                         (df["Algorithm"] == baseline) &
                         (df["boundValues"] == row['boundValues'])]
        if relateastar.empty:
            print("error! baseline not found")
            differenceNodeGen.append(np.nan)
        else:
            diffNodeGen = row['nodeGen'] / relateastar['nodeGen']
            # print("row",row)
            # print("relateastar",relateastar)
            diffNodeGen = diffNodeGen.values[0]
            differenceNodeGen.append(diffNodeGen)

    df["nodeGenDiff"] = differenceNodeGen

    return df


def allSolvedDf(rawdf):
    df = pd.DataFrame()
    df["Algorithm"] = np.nan
    df["instance"] = np.nan
    df["boundValues"] = np.nan
    df["nodeGen"] = np.nan
    df["nodeExp"] = np.nan
    df["cpu"] = np.nan

    algorithms = rawdf["Algorithm"].unique()

    for instance in rawdf["instance"].unique():
        dfins = rawdf[rawdf["instance"] == instance]
        # keep instances solved by all algorithms across all bounds
        if len(dfins) == len(algorithms) * len(rawdf["boundValues"].unique()):
            df = df.append(dfins)

    # for instance in rawdf["instance"].unique():
        # for boundP in rawdf["boundValues"].unique():
            # # print(instance, boundP)
            # dfins = rawdf[(rawdf["instance"] == instance) &
            # (rawdf["boundValues"] == boundP)]

            # if len(dfins) == len(algorithms):  # keep instances solved by all algorithms
            # df = df.append(dfins)

    boundValues = rawdf["boundValues"].unique()
    boundValues.sort()
    for boundV in boundValues:
        print("bound percent ", boundV, "valid instances: ", len(
            df[df["boundValues"] == boundV]["instance"].unique()))

    return df


def makePar10Df(rawdf, totalInstance):

    par10Algorithm = []
    par10BoundValue = []
    par10Cpu = []
    par10Instance = []
    par10NodeExpanded = []
    par10NodeGenerated = []

    boundValues = rawdf["boundValues"].unique()
    boundValues.sort()
    algorithms = rawdf["Algorithm"].unique()

    maxCPU = rawdf["cpu"].max()
    maxNodeGen = rawdf["nodeGen"].max()
    maxNodeExp = rawdf["nodeExp"].max()
    for alg in algorithms:
        for boundV in boundValues:
            dfins = rawdf[(rawdf["Algorithm"] == alg) &
                          (rawdf["boundValues"] == boundV)]
            numberUnsolved = int(totalInstance) - len(dfins)
            if numberUnsolved > 0:
                for i in range(numberUnsolved):
                    par10Instance.append("par10-"+str(i))
                    par10Algorithm.append(alg)
                    par10BoundValue.append(boundV)
                    par10Cpu.append(maxCPU*10)
                    par10NodeGenerated.append(maxNodeGen*10)
                    par10NodeExpanded.append(maxNodeExp*10)

    par10df = pd.DataFrame({
        "Algorithm": par10Algorithm,
        "instance": par10Instance,
        "boundValues": par10BoundValue,
        "nodeGen": par10NodeGenerated,
        "nodeExp": par10NodeExpanded,
        "cpu": par10Cpu,
    })

    df = pd.DataFrame()
    df["Algorithm"] = np.nan
    df["instance"] = np.nan
    df["boundValues"] = np.nan
    df["nodeGen"] = np.nan
    df["nodeExp"] = np.nan
    df["cpu"] = np.nan

    df = df.append(rawdf)
    df = df.append(par10df)

    return df

def makeTimeUpperBoundDf(rawdf, totalInstance):

    timeLimitAlgorithm = []
    timeLimitBoundValue = []
    timeLimitCpu = []
    timeLimitInstance = []

    boundValues = rawdf["boundValues"].unique()
    boundValues.sort()
    algorithms = rawdf["Algorithm"].unique()

    for alg in algorithms:
        for boundV in boundValues:
            dfins = rawdf[(rawdf["Algorithm"] == alg) &
                          (rawdf["boundValues"] == boundV)]
            numberUnsolved = int(totalInstance) - len(dfins)
            if numberUnsolved > 0:
                for i in range(numberUnsolved):
                    timeLimitInstance.append("TimeLimitReached-"+str(i))
                    timeLimitAlgorithm.append(alg)
                    timeLimitBoundValue.append(boundV)
                    timeLimitCpu.append(600)

    timeLimitdf = pd.DataFrame({
        "Algorithm": timeLimitAlgorithm,
        "instance": timeLimitInstance,
        "boundValues": timeLimitBoundValue,
        "cpu": timeLimitCpu,
    })

    df = pd.DataFrame()
    df["Algorithm"] = np.nan
    df["instance"] = np.nan
    df["boundValues"] = np.nan
    df["cpu"] = np.nan

    df = df.append(rawdf)
    df = df.append(timeLimitdf)

    return df


def readData(args, algorithms, domainBoundsConfig):
    domainSize = args.size
    domainType = args.domain
    subdomainType = args.subdomain

    algorithm = []
    boundValue = []
    cpu = []
    instance = []
    nodeExpanded = []
    nodeGenerated = []

    print("reading in data...")

    resultDir = "results"

    domainDir = domainType

    inPath = "../../../" + resultDir + "/" + \
        domainDir + "/" + subdomainType

    if domainType in ["racetrack", "pancake"]:
        inPath += "/"+args.heuristicType

    inPath += '/alg'

    for alg in algorithms:
        print("reading ", alg)

        inPath_alg = inPath.replace('alg', alg)
        for jsonFile in os.listdir(inPath_alg):
            if jsonFile[-5:] != ".json":
                continue

            numbersInFileName = re.findall(r'\d*\.?\d+', jsonFile)
            sizeStr = numbersInFileName[1]

            if domainType == "pancake" and sizeStr != domainSize:
                continue

            boundValueStr = numbersInFileName[0]
            boundV = float(boundValueStr)

            lowerBound = float(args.boundPercentStart)
            upperBound = float(args.boundPercentEnd)
            allAvailableBoundValue = \
                domainBoundsConfig["avaiableBoundPercent"][args.domain][args.subdomain]

            if(boundV < lowerBound or
               boundV > upperBound or
               (boundV not in allAvailableBoundValue)):
                continue

            try:
                with open(inPath_alg + "/" + jsonFile) as json_data:

                    resultData = json.load(json_data)

                    # if alg == "ptsnancy":
                    # if alg == "ptsnancy" and resultData["node generated"] > 1000:
                    # print("reading ", alg, jsonFile, "generated: ",
                    # resultData["node generated"])

                    # if alg == "ptsnancy" and resultData["node generated"] > 1000:
                    # continue

                    algorithm.append(algorithms[alg])
                    boundValue.append(boundV)
                    cpu.append(resultData["cpu time"])
                    instance.append(resultData["instance"])
                    nodeExpanded.append(resultData["node expanded"])
                    nodeGenerated.append(resultData["node generated"])
            except JSONDecodeError as e:
                print("json error:", e)
                print("when reading ", alg, jsonFile)
                sys.exit(1)

    rawdf = pd.DataFrame({
        "Algorithm": algorithm,
        "instance": instance,
        "boundValues": boundValue,

        "nodeGen": nodeGenerated,
        "nodeExp": nodeExpanded,
        "cpu": cpu,
    })

    # print rawdf
    return rawdf

def makeCoverageTable(df, args, totalInstance):
    out_file = createOutFilePrefix(args) + args.plotType+".jpg"

    algs = []

    boundSolved = {}

    boundStr = df["boundValues"].unique()
    bounds = [float(i) for i in boundStr]
    bounds.sort()

    for cbound in bounds:
        boundSolved[str(cbound)] = []

    for alg in df["Algorithm"].unique():

        algs.append(alg)

        for cbound in df["boundValues"].unique():
            dfins = df[(df["Algorithm"] == alg) & (
                df["boundValues"] == cbound)]
            boundSolved[str(float(cbound))].append(
                str(len(dfins))+"/"+totalInstance)

    data = {"Algorihtm": algs}
    data.update(boundSolved)

    nrows, ncols = len(algs)+1, len(bounds)
    hcell, wcell = 0.3, 1
    hpad, wpad = 0, 0
    fig = plt.figure(figsize=(ncols*wcell+wpad, nrows*hcell+hpad))
    ax = fig.add_subplot(111)
    ax.axis('off')

    tabledf = pd.DataFrame(data)

    # ax = plt.subplot(frame_on=False)  # no visible frame
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis

    table(ax, tabledf, loc='center')  # where tabledf is your data frame

    plt.savefig(out_file, dpi=200)

def makeCoveragePlot(df, args, totalInstance, showname, colorDict):
    algs = []
    bound = []
    solved = []

    for alg in df["Algorithm"].unique():
        for cbound in df["boundValues"].unique():
            algs.append(alg)
            bound.append(cbound)
            dfins = df[(df["Algorithm"] == alg) & (
                df["boundValues"] == cbound)]
            solved.append(len(dfins))

    rawdf = pd.DataFrame({
        "Algorithm": algs,
        "boundValues": bound,
        "solved": solved
    })

    makeLinePlot("boundValues", "solved", rawdf, "Algorithm",
                 showname["boundValues"],
                 showname["solved"].replace(
                     "totalInstance", totalInstance), totalInstance,
                 createOutFilePrefix(args) + args.plotType+".jpg", colorDict,
                 createTitle(args), showSolvedInstance=False, useLogScale=False)


def createOutFilePrefix(args):

    nowstr = datetime.now().strftime("%d%m%Y-%H%M%S")

    outDirectory = "../../../plots/" + args.domain

    if args.outTime != 'NA':
        outDirectory = "../../../plots/" + args.outTime + "/" + args.domain

    if not os.path.exists(outDirectory):
        os.makedirs(outDirectory, exist_ok=True)

    outFilePrefix = outDirectory + '/' + args.domain + "-" + \
        args.subdomain + "-"

    if args.domain == 'pancake':
        outFilePrefix += args.size + "-"
        if args.subdomain == "regular":
            outFilePrefix += args.heuristicType + "-"
    elif args.domain == "racetrack":
        outFilePrefix += args.heuristicType + "-"

    if args.outTime == 'NA':
        outFilePrefix += nowstr + "-"

    if args.outSuffix != 'NA':
        outFilePrefix += args.outSuffix + "-"

    if args.removeAlgorithm:
        for alg in args.removeAlgorithm:
            outFilePrefix += "no-"+ alg + "-"

    return outFilePrefix


def createTitle(args):
    title = {"tile": {"uniform": "Uniform Tile",
                      "heavy": "Heavy Tile",
                      "heavy-easy": "Easy Heavy Tile",
                      "inverse": "Inverse Tile",
                      "reverse-easy": "Easy Reverse Tile",
                      "sqrt": "Sqrt Tile", },
             "pancake": {"regular": args.size+" Regular Pancake - " +
                         args.heuristicType.replace('m', '-').capitalize(),
                         "heavy": args.size+" DPS Heavy Pancake",
                         "sumheavy": args.size+" Sum Heavy Pancake",
                         },
             "vacuumworld": {"uniform": "Uniform Vacuum World",
                             "heavy-easy": "Easy Heavy Vacuum World"},
             "racetrack": {"barto-bigger": "Barto Map Track - "+args.heuristicType.capitalize(),
                           "hansen-bigger": "Hansen Map Track - "+args.heuristicType.capitalize(),
                           }
             }

    return title[args.domain][args.subdomain]


def plotting(args, config):
    print("building plots...")

    algorithms = config.getAlgorithms(args.removeAlgorithm)

    showname = config.getShowname()
    totalInstance = config.getTotalInstance()

    rawdf = readData(args, algorithms, config.getDomainBoundsConfig())

    if args.plotType == "coveragetb":
        makeCoverageTable(rawdf, args, totalInstance[args.domain])
    elif args.plotType == "coverageplt":
        makeCoveragePlot(rawdf, args, totalInstance[args.domain],
                         showname, config.getAlgorithmColor())
    elif args.plotType == "par10":

        df = makePar10Df(rawdf, totalInstance[args.domain])

        makeLinePlot("boundValues", "cpu", df, "Algorithm",
                     showname["boundValues"],
                     "Par10 CPU Time", totalInstance[args.domain],
                     createOutFilePrefix(args) + args.plotType+".jpg",
                     config.getAlgorithmColor(), createTitle(args), showSolvedInstance=False)
    elif args.plotType == "timelimitcpu":

        df = makeTimeUpperBoundDf(rawdf, totalInstance[args.domain])

        makeLinePlot("boundValues", "cpu", df, "Algorithm",
                     showname["boundValues"],
                     "raw CPU Time", totalInstance[args.domain],
                     createOutFilePrefix(args) + args.plotType+".jpg",
                     config.getAlgorithmColor(), createTitle(args), showSolvedInstance=False)

    else:
        df = allSolvedDf(rawdf)
        makeLinePlot("boundValues", args.plotType, df, "Algorithm",
                     showname["boundValues"], showname[args.plotType],
                     totalInstance[args.domain],
                     createOutFilePrefix(args) + args.plotType+".jpg",
                     config.getAlgorithmColor(), createTitle(args))


def main():
    parser = parseArugments()
    args = parser.parse_args()
    print(args)

    plotting(args, Configure())


if __name__ == '__main__':
    main()
