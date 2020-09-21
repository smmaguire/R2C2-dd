#!/usr/bin/env python3
# Roger Volden and Chris Vollmers
# Last updated: 2 Aug 2018

'''
Concatemeric Consensus Caller with Partial Order Alignments (C3POa)

Analyses reads by reading them in, doing self-self alignments, calling
peaks in alignment scores,  splitting reads, aligning those to each other,
and giving back a consensus sequence.

Usage:
    python3 C3POa.py --reads reads.fastq [--path /current/directory]

Dependencies:
    Python 3.6
    NumPy 1.13.3
    poa v1.0.0 Revision: 1.2.2.9500
    EMBOSS water: watHerON v8
    minimap2 2.7-r654
    racon

02/08/2018 Release note:
    By default, this will now output what we call zero repeat reads along
    with the rest of the R2C2 reads. Zero repeat reads are reads that contain
    a splint with incomplete portions of your original molecule on each side.
    If there's an overlap, it'll align the portions that overlap and
    concatenate the rest of the read together to try and make a contiguous
    read. These reads are very similar to normal 1D reads, but there are a few
    cases where there is a slight improvement. There will be an option to
    remove these reads in postprocessing.
'''

import os
import sys
import numpy as np
import argparse

def argParser():
    '''Parses arguments.'''
    parser = argparse.ArgumentParser(description = 'Makes consensus sequences \
                                                    from R2C2 reads.',
                                     add_help = True,
                                     prefix_chars = '-')
    required = parser.add_argument_group('required arguments')
    required.add_argument('--reads', '-r', type=str, action='store', required=True,
                          help='FASTQ file that contains the long R2C2 reads.')
    parser.add_argument('--path', '-p', type=str, action='store', default=os.getcwd(),
                        help='Directory where all the files are/where they will end up.\
                              Defaults to your current directory.')
    parser.add_argument('--matrix', '-m', type=str, action='store',
                        default='NUC.4.4.mat',
                        help='Score matrix to use for poa.\
                              Defaults to NUC.4.4.mat.')
    parser.add_argument('--config', '-c', type=str, action='store', default='',
                        help='If you want to use a config file to specify paths to\
                              programs, specify them here. Use for poa, racon, water,\
                              blat, and minimap2 if they are not in your path.')
    parser.add_argument('--slencutoff', '-l', type=int, action='store', default=1000,
                        help='Sets the length cutoff for your raw sequences. Anything\
                              shorter than the cutoff will be excluded. Defaults to 1000.')
    parser.add_argument('--mdistcutoff', '-d', type=int, action='store', default=500,
                        help='Sets the median distance cutoff for consensus sequences.\
                              Anything shorter will be excluded. Defaults to 500.')
    parser.add_argument('--output', '-o', type=str, action='store',
                        default='R2C2_Consensus.fasta',
                        help='FASTA file that the consensus gets written to.\
                              Defaults to R2C2_Consensus.fasta')
    parser.add_argument('--timer', '-t', type=bool, action='store',
                        default=False, help='Prints how long each dependency takes to run.\
                                             Defaults to False')
    parser.add_argument('--figure', '-f', type=bool, action='store', default=False,
                        help='Set to true if you want to output a histogram of scores.')
    return vars(parser.parse_args())

def configReader(configIn):
    '''Parses the config file.'''
    progs = {}
    for line in open(configIn):
        if line.startswith('#') or not line.rstrip().split():
            continue
        line = line.rstrip().split('\t')
        progs[line[0]] = line[1]
    # should have minimap, poa, racon, water, consensus
    # check for extra programs that shouldn't be there
    possible = set(['poa', 'minimap2', 'water', 'consensus', 'racon', 'blat'])
    inConfig = set()
    for key in progs.keys():
        inConfig.add(key)
        if key not in possible:
            raise Exception('Check config file')
    # check for missing programs
    # if missing, default to path
    for missing in possible-inConfig:
        if missing == 'consensus':
            path = 'consensus.py'
        else:
            path = missing
        progs[missing] = path
        sys.stderr.write('Using ' + str(missing)
                         + ' from your path, not the config file.\n')
    return progs

args = argParser()
if args['config']:
    progs = configReader(args['config'])
    minimap2 = progs['minimap2']
    poa = progs['poa']
    racon = progs['racon']
    water = progs['water']
    consensus = progs['consensus']
else:
    minimap2, poa, racon, water = 'minimap2', 'poa', 'racon', 'water'
    consensus = 'consensus.py'

consensus = 'python3 ' + consensus
path = args['path']
temp_folder = path + '/' + 'tmp1'
input_file = args['reads']
score_matrix = args['matrix']

seqLenCutoff = args['slencutoff']
medDistCutoff = args['mdistcutoff']

out_file = args['output']
timer = args['timer']
figure = args['figure']
subread_file = 'subreads.fastq'
os.chdir(path)
sub = open(path + '/' + subread_file, 'w')
os.system('rm -r ' + temp_folder)
os.system('mkdir ' + temp_folder)

def revComp(sequence):
    '''Returns the reverse complement of a sequence'''
    bases = {'A':'T', 'C':'G', 'G':'C', 'T':'A', 'N':'N', '-':'-'}
    return ''.join([bases[x] for x in list(sequence)])[::-1]

def split_read(split_list, sequence, out_file1, qual, out_file1q, name):
    '''
    split_list : list, peak positions
    sequence : strprint(timer)
exit()
    out_file1 : output FASTA file
    qual : str, quality line from FASTQ
    out_file1q : output FASTQ file
    name : str, read ID

    Writes sequences to FASTA and FASTQ files.
    Returns number of repeats in the sequence.
    '''
    out_F = open(out_file1, 'w')
    out_Fq = open(out_file1q, 'w')
    for i in range(len(split_list) - 1):
        split1 = split_list[i]
        split2 = split_list[i+1]
        if len(sequence[split1:split2]) > 30:
            out_F.write('>' + str(i + 1) + '\n' \
                        + sequence[split1:split2] + '\n')
            out_Fq.write('@' + str(i + 1) + '\n' \
                         + sequence[split1:split2] + '\n+\n' \
                         + qual[split1:split2] + '\n')
            sub.write('@' + name + '_' + str(i + 1) +' \n' \
                      + sequence[split1:split2] + '\n+\n' \
                      + qual[split1:split2] + '\n')

    if len(sequence[:split_list[0]]) > 50:
        out_Fq.write('@' + str(0) + '\n' \
                     + sequence[0:split_list[0]] + '\n+\n' \
                     + qual[0:split_list[0]] + '\n')
        sub.write('@' + name + '_' + str(0) + '\n' \
                  + sequence[0:split_list[0]] + '\n+\n' \
                  + qual[0:split_list[0]] + '\n')

    if len(sequence[split2:]) > 50:
        out_Fq.write('@' + str(i + 2) + '\n' \
                     + sequence[split2:] + '\n+\n' \
                     + qual[split2:] + '\n')
        sub.write('@' + name + '_' + str(i + 2) + '\n' \
                  + sequence[split2:] + '\n+\n' \
                  + qual[split2:] + '\n')
    repeats = str(int(i + 1))
    out_F.close()
    out_Fq.close()
    return repeats

def read_fasta(inFile):
    '''Reads in FASTA files, returns a dict of header:sequence'''
    readDict = {}
    tempSeqs, headers, sequences = [], [], []
    for line in open(inFile):
        line = line.rstrip()
        if not line:
            continue
        if line.startswith('>'):
            headers.append(line.split()[0][1:])
        # covers the case where the file ends while reading sequences
        if line.startswith('>'):
            sequences.append(''.join(tempSeqs).upper())
            tempSeqs = []
        else:
            tempSeqs.append(line)
    sequences.append(''.join(tempSeqs).upper())
    sequences = sequences[1:]
    for i in range(len(headers)):
        readDict[headers[i]] = sequences[i]
    return readDict

# def read_fasta(inFile):
#     '''Reads in FASTA files, returns a dict of header:sequence'''
#     readDict = {}
#     for line in open(inFile):
#         line = line.rstrip()
#         if not line:
#             continue
#         if line.startswith('>'):
#             readDict[line[1:]] = ''
#             lastHead = line[1:]
#         else:
#             readDict[lastHead] += line
#     return readDict

def rounding(x, base):
    '''Rounds to the nearest base, we use 50'''
    return int(base * round(float(x)/base))

def makeFig(scoreList_F, scoreList_R, peakList_R, seed, filtered_peaks):
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import matplotlib.patches as mplpatches
    # plt.style.use('BME163')
    plt.figure(figsize = (10, 5))
    hist = plt.axes([0.1, 0.1, 8/10, 4/5], frameon = True)

    xlist = [x for x in range(0, len(filtered_peaks))]
    hist.plot(xlist, filtered_peaks, color =  (0, 68/255, 85/255), \
              lw = 1, zorder = 550)
    ylim = max(scoreList_F) * 1.1
    ymin = min(filtered_peaks)*1.1
    xlim = (len(scoreList_F) + seed)
    wholeSeq = mplpatches.Rectangle((0, -15000), xlim, 30000, lw = 0, \
                                    fc = 'grey', zorder = 1000)
    hist.add_patch(wholeSeq)
    for i in range(seed, xlim):
        if np.in1d(i, peakList_R):
            color = (0.3, 0.3, 0.3)
            if i == seed:
                color = 'black'
            bar1 = mplpatches.Rectangle((i-12.5, filtered_peaks[i]), 25, ylim, \
                                        lw = 0, fc = (0.96, 0.43, 0.2), zorder = 0)
            hist.add_patch(bar1) # 253/255, 177/255, 85/255
            splint = mplpatches.Rectangle((i-150, -15000), 300, 30000, \
                                          lw = 0, fc = color, zorder = 1100)
            hist.add_patch(splint)
        else:
            bar3 = mplpatches.Rectangle((i, 0), 3, scoreList_F[i-seed], lw = 0, \
                                       facecolor = (0, 191/255, 165/255), zorder = 100)
            hist.add_patch(bar3)

    for j in range(len(scoreList_R), 1, -1):
        if np.in1d(j, peakList_R):
            color = (0.3, 0.3, 0.3)
            if i == seed:
                color = 'black'
            bar5 = mplpatches.Rectangle((j-12.5, 0), 25, -ylim, lw = 0, \
                                        fc = (0.96, 0.43, 0.2), zorder = 0)
            hist.add_patch(bar5)
            splint = mplpatches.Rectangle((j-150, -15000), 300, 30000, lw = 0, \
                                          fc = color, zorder = 1100)
            hist.add_patch(splint)
        try:
            bar6 = mplpatches.Rectangle((j, 0), 3, -scoreList_R[seed-j], lw = 0, \
                                       facecolor = (0, 191/255, 165/255), zorder = 100)
            hist.add_patch(bar6)
        except IndexError:
            pass

    hist.set_ylim(ymin, ylim)
    hist.set_xlim(0, xlim)
    hist.set_ylabel('Alignment Score', fontsize = 11, labelpad = 6.5)
    hist.set_xlabel('Read position', fontsize = 11, labelpad = 6)
    hist.tick_params(axis='both',which='both',\
                     bottom='on', labelbottom='on',\
                     left='on', labelleft='on',\
                     right='off', labelright='off',\
                     top='off', labeltop='off')

    plt.savefig('plumetest.png', dpi = 600)
    plt.close()
    sys.exit()

def savitzky_golay(y, window_size, order, deriv=0, rate=1, returnScoreList=False):
    '''
    Smooths over data using a Savitzky Golay filter
    This can either return a list of scores, or a list of peaks

    y : array-like, score list
    window_size : int, how big of a window to smooth
    order : what order polynomial
    returnScoreList : bool
    '''
    from math import factorial
    y = np.array(y)
    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half, half + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with values taken from the signal itself
    firstvals = y[0] - np.abs( y[1:half+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    filtered = np.convolve( m[::-1], y, mode='valid')

    if returnScoreList:
        return np.convolve( m[::-1], y, mode='valid')

    # set everything between 1 and -inf to 1
    posFiltered = []
    for i in range(len(filtered)):
        if 1 > filtered[i] >= -np.inf:
            posFiltered.append(1)
        else:
            posFiltered.append(filtered[i])

    # use slopes to determine peaks
    peaks = []
    slopes = np.diff(posFiltered)
    la = 45 # how far in sequence to look ahead
    for i in range(len(slopes) - 50):
        if i > len(slopes) - la: # probably irrelevant now
            dec = all(slopes[i+x] < 0 for x in range(1, 50))
            if slopes[i] > 0 and dec:
                if i not in peaks:
                    peaks.append(i)
        else:
            dec = all(slopes[i+x] < 0 for x in range(1, la))
            if slopes[i] > 0 and dec:
                peaks.append(i)
    return peaks

def callPeaks(scoreListF, scoreListR, seed):
    '''
    scoreListF : list of forward scores
    scoreListR : list of reverse scores
    seed : position of the first occurrence of the splint
    returns a sorted list of all peaks
    '''
    allPeaks = []
    allPeaks.append(seed)
    # Filter out base level noise in forward scores
    if not scoreListF:
        smoothedScoresF = []
    else:
        noise = 0
        try:
            for i in range(500):
                if scoreListF[i] > noise:
                    noise = scoreListF[i]
            for j in range(len(scoreListF)):
                if scoreListF[j] <= noise*1.25:
                    scoreListF[j] = 1
        except IndexError:
            pass
        # Smooth over the data multiple times
        smoothedScoresF = savitzky_golay(scoreListF, 51, 2, deriv = 0, \
                                         rate = 1, returnScoreList = True)
        for iteration in range(3):
            smoothedScoresF = savitzky_golay(smoothedScoresF, 71, 2, deriv = 0, \
                                             rate = 1, returnScoreList = True)
        peaksF = savitzky_golay(smoothedScoresF, 51, 1, deriv = 0, \
                                rate = 1, returnScoreList = False)
        # Add all of the smoothed peaks to list of all peaks
        peaksFAdj = list(seed + np.array(peaksF))
        allPeaks += peaksFAdj

    # Covers the case where the seed is 0
    if not scoreListR:
        smoothedScoresR = []
    # Do the same-ish thing for the reverse peaks
    else:
        noise = 0
        try:
            for i in range(100):
                if scoreListR[i] > noise:
                    noise = scoreListR[i]
            for j in range(len(scoreListR)):
                if scoreListR[j] <= noise*1.15:
                    scoreListR[j] = 1
        except IndexError:
            pass
        smoothedScoresR = savitzky_golay(scoreListR, 51, 2, deriv = 0, \
                                         rate = 1, returnScoreList = True)
        for iteration in range(3):
            smoothedScoresR = savitzky_golay(smoothedScoresR, 71, 2, deriv = 0, \
                                             rate = 1, returnScoreList = True)
        peaksR = savitzky_golay(smoothedScoresR, 51, 1, deriv = 0, \
                                rate = 1, returnScoreList = False)
        peaksRAdj = list(seed - np.array(peaksR))
        allPeaks += peaksRAdj

    smoothedPeaks = []
    for thing in [-x for x in smoothedScoresR[::-1]]:
        smoothedPeaks.append(thing)
    for thing in smoothedScoresF:
        smoothedPeaks.append(thing)
    sortedPeaks = sorted(list(set(allPeaks)))

    finalPeaks = []
    for i in range(0, len(sortedPeaks)):
        if i == 0:
            finalPeaks.append(sortedPeaks[i])
        elif sortedPeaks[i-1] < sortedPeaks[i] < sortedPeaks[i-1] + 200:
            continue
        else:
            finalPeaks.append(sortedPeaks[i])
    if figure:
        return finalPeaks, smoothedPeaks
    # calculates the median distance between detected peaks
    forMedian = []
    for i in range(len(finalPeaks) - 1):
        forMedian.append(finalPeaks[i+1] - finalPeaks[i])
    forMedian = [rounding(x, 50) for x in forMedian]
    medianDistance = np.median(forMedian)
    return finalPeaks, medianDistance

def water_parser():
    '''
    Parses the water output and returns the indeces where the read starts
    repeating on itself. Used for determining where to start the partial
    consensus reads because peaks are not base accurate.
    Also writes the sequences themselves to a file because I need the gaps
    to use consensus.py to make a better partial consensus.
    '''
    alignFile, lineNum = temp_folder + '/align.whatever', 0
    posFirstSeq, posSecondSeq = [], []
    # temporary lists to build the sequences with gaps
    tempFirst, tempSecond = [], []
    for line in open(alignFile):
        line = line.strip()
        if not line or line.startswith('#') or '|' in line:
            continue
        seq = line.split()[2]
        if lineNum % 2 == 0:
            tempFirst.append(seq)
            posFirstSeq.append(int(line.split()[1]))
            posFirstSeq.append(int(line.split()[3]))
        else:
            tempSecond.append(seq)
            posSecondSeq.append(int(line.split()[1]))
            posSecondSeq.append(int(line.split()[3]))
        lineNum += 1
    partialConsensus = open(temp_folder + '/partial.fasta', 'w+')
    partialConsensus.write('>First' + '\n' + ''.join(tempFirst) + '\n')
    partialConsensus.write('>Second' + '\n' + ''.join(tempSecond))
    partialConsensus.close()
    firstSeqIndeces = (posFirstSeq[0] - 1, posFirstSeq[-1] - 1)
    secondSeqIndeces = (posSecondSeq[0] - 1, posSecondSeq[-1] - 1)

    return firstSeqIndeces, secondSeqIndeces

def run_water(step, seq1, seq2, totalLen, diag_dict, diag_set):
    '''
    Runs water using the parameters given by split_SW
    '''
    diagonal = 'no'
    if step == 0:
        diagonal = 'yes'

    x_limit, y_limit = len(seq1), len(seq2)

    os.system('%s -asequence seq1.fasta -bsequence seq2.fasta \
              -datafile EDNAFULL -gapopen 25 -outfile=%s/align.whatever \
              -gapextend 1  %s %s %s >./sw.txt 2>&1' \
              %(water, temp_folder, diagonal, x_limit, y_limit))
    matrix_file = 'SW_PARSE.txt'
    diag_set, diag_dict = parse_file(matrix_file, totalLen, step, \
                                     diag_set, diag_dict)
    os.system('rm SW_PARSE.txt SW_PARSE_PARTIAL.txt sw.txt')
    return diag_set, diag_dict

def split_SW(name, seq, step):
    '''
    Takes a sequence and does the water alignment to itself
    Returns a list of scores from summing diagonals from the
    alignment matrix.
    name (str): the sequence header
    seq (str): nucleotide sequence
    step (bool): if false, aligns entire sequence to itself
    '''
    totalLen = len(seq)
    diag_dict, diag_set = {}, set()
    if step:
        for step in range(0, len(seq), 1000):
            seq1 = seq[step:min(len(seq), step + 1000)]
            seq2 = seq[:1000]
            align_file1 = open('seq1.fasta', 'w')
            align_file1.write('>' + name + '\n' + seq1 + '\n')
            align_file1.close()
            align_file2 = open('seq2.fasta', 'w')
            align_file2.write('>' + name + '\n' + seq2 + '\n')
            align_file2.close()

            run_water(step, seq1, seq2, totalLen, diag_dict, diag_set)
    else:
        step = 0
        align_file1 = open('seq1.fasta', 'w')
        align_file1.write('>' + name + '\n' + seq + '\n')
        align_file1.close()
        align_file2 = open('seq2.fasta', 'w')
        align_file2.write('>' + name + '\n' + seq + '\n')
        align_file2.close()

        run_water(step, seq, seq, totalLen, diag_dict, diag_set)

    diag_set = sorted(list(diag_set))
    plot_list = []
    for diag in diag_set:
        plot_list.append(diag_dict[diag])
    return plot_list

def parse_file(matrix_file, seq_length, step, diag_set, diag_dict):
    '''
    matrix_file : watHerON output file
    seq_length : int, length of the sequence
    step : int, some position
    Returns:
        diag_set : set, positions
        diag_dict : dict, position : diagonal alignment scores
    '''
    for line in open(matrix_file):
        line = line.strip().split(':')
        position = int(line[0]) + step
        position = np.abs(position)
        value = int(line[1]) # actual score
        diag_set.add(position)
        try:
            diag_dict[position] += value
        except:
            diag_dict[position] = value
    return diag_set, diag_dict

# def determine_consensus(name, seq, peaks, qual, median_distance, seed):
#     '''
#     Aligns and returns the consensus depending on the number of repeats
#     If there are multiple peaks, it'll do the normal partial order
#     alignment with racon correction
#     If there are two repeats, it'll do the special pairwise consensus
#     making
#     Otherwise, it'll try to make a 0 repeat consensus: reads with a splint
#     in the middle where you can try to salvage the flanking sequences to
#     try and make a complete read
#     '''
#     repeats = ''
#     corrected_consensus = ''
#     if median_distance > medDistCutoff and len(peaks) > 1:
#         out_F = temp_folder + '/' + name + '_F.fasta'
#         out_Fq = temp_folder + '/' + name + '_F.fastq'
#         poa_cons = temp_folder + '/' + name + '_consensus.fasta'
#         final = temp_folder + '/' + name + '_corrected_consensus.fasta'
#         overlap = temp_folder +'/' + name + '_overlaps.sam'
#         pairwise = temp_folder + '/' + name + '_prelim_consensus.fasta'
#         repeats = split_read(peaks, seq, out_F, qual, out_Fq, name)

#         PIR = temp_folder + '/' + name + 'alignment.fasta'
#         os.system('%s -read_fasta %s -hb -pir %s \
#                   -do_progressive %s >./poa_messages.txt 2>&1' \
#                   %(poa, out_F, PIR, score_matrix))
#         reads = read_fasta(PIR)

#         if repeats == '2':
#             Qual_Fasta = open(pairwise, 'w')
#             for read in reads:
#                 if 'CONSENS' not in read:
#                     Qual_Fasta.write('>' + read + '\n' + reads[read] + '\n')
#             Qual_Fasta.close()
#             os.system('%s %s %s %s >> %s' \
#                       %(consensus, pairwise, out_Fq, name, poa_cons))

#         else:
#             for read in reads:
#               if 'CONSENS0' in read:
#                 out_cons_file = open(poa_cons, 'w')
#                 out_cons_file.write('>' + name + '\n' \
#                                     + reads[read].replace('-', '') + '\n')
#                 out_cons_file.close()

#         final = poa_cons
#         for i in np.arange(1, 2, 1):
#             try:
#                 if i == 1:
#                     input_cons = poa_cons
#                     output_cons = poa_cons.replace('.fasta', '_' + str(i) + '.fasta')
#                 else:
#                     input_cons = poa_cons.replace('.fasta', '_' + str(i-1) + '.fasta')
#                     output_cons = poa_cons.replace('.fasta', '_' + str(i) + '.fasta')

#                 os.system('%s --secondary=no -ax map-ont \
#                           %s %s > %s 2> ./minimap2_messages.txt' \
#                           %(minimap2, input_cons, out_Fq, overlap))

#                 os.system('%s -q 5 -t 1 \
#                           %s %s %s >%s 2>./racon_messages.txt' \
#                           %(racon,out_Fq, overlap, input_cons, output_cons))
#                 final = output_cons
#             except:
#                 pass
#         print(final)
#         reads = read_fasta(final)
#         for read in reads:
#             corrected_consensus = reads[read]

#     # reads that have the potential for a partial consensus
#     elif len(peaks) == 1:
#         # before/after positions are the alignment start/end positions for
#         # both portions of the sequence
#         beforeIndeces, afterIndeces = water_parser()
#         endPortion = seq[beforeIndeces[1]:seed]
#         begPortion = seq[seed:afterIndeces[0]]

#         # make a temporary FASTQ file for consensus.py with portions
#         # of reads that match itself
#         tempFastqName = temp_folder + '/' + name + 'consensusFastq.fastq'
#         tempFastq = open(tempFastqName, 'w+')
#         tempFastq.write('@' + name + '\n'
#                         + seq[beforeIndeces[0]:beforeIndeces[1] + 1] + '\n+\n'
#                         + qual[beforeIndeces[0]:beforeIndeces[1] + 1] + '\n'
#                         + '@' + name + '\n'
#                         + seq[afterIndeces[0]:afterIndeces[1] + 1] + '\n+\n'
#                         + qual[afterIndeces[0]:afterIndeces[1] + 1])
#         tempFastq.close()
#         alignedFasta = temp_folder + '/partial.fasta'
#         fromConsensus = temp_folder + '/' + name + '_fromConsensus.fasta'
#         os.system('%s %s %s > %s'
#                   %(consensus, alignedFasta, tempFastqName, fromConsensus))
#         toGetConsensus = read_fasta(fromConsensus)
#         seqFromCons = toGetConsensus['consensus']
#         # put all the pieces back together to make the consensus
#         corrected_consensus = begPortion + seqFromCons + endPortion
#         repeats = '0'

#     return corrected_consensus, repeats


def determine_consensus(name, seq, peaks, qual, median_distance, seed):
    '''
    Aligns and returns the consensus depending on the number of repeats
    If there are multiple peaks, it'll do the normal partial order
    alignment with racon correction
    If there are two repeats, it'll do the special pairwise consensus
    making
    Otherwise, it'll try to make a 0 repeat consensus: reads with a splint
    in the middle where you can try to salvage the flanking sequences to
    try and make a complete read
    '''
    from time import time
    repeats = ''
    corrected_consensus = ''
    if median_distance > medDistCutoff and len(peaks) > 1:
        out_F = temp_folder + '/' + name + '_F.fasta'
        out_Fq = temp_folder + '/' + name + '_F.fastq'
        poa_cons = temp_folder + '/' + name + '_consensus.fasta'
        final = temp_folder + '/' + name + '_corrected_consensus.fasta'
        overlap = temp_folder +'/' + name + '_overlaps.sam'
        pairwise = temp_folder + '/' + name + '_prelim_consensus.fasta'
        repeats = split_read(peaks, seq, out_F, qual, out_Fq, name)

        PIR = temp_folder + '/' + name + 'alignment.fasta'
        poa_start = time()
        os.system('%s -read_fasta %s -hb -pir %s \
                  -do_progressive %s >./poa_messages.txt 2>&1' \
                  %(poa, out_F, PIR, score_matrix))
        poa_stop = time()
        if timer:
            print('POA took ' + str(poa_stop - poa_start) + ' seconds to run.')
        reads = read_fasta(PIR)

        if repeats == '2':
            Qual_Fasta = open(pairwise, 'w')
            for read in reads:
                if 'CONSENS' not in read:
                    Qual_Fasta.write('>' + read + '\n' + reads[read] + '\n')
            Qual_Fasta.close()
            conspy_start = time()
            os.system('%s %s %s %s >> %s' \
                      %(consensus, pairwise, out_Fq, name, poa_cons))
            conspy_stop = time()
            if timer:
                print('consensus.py took ' + str(conspy_stop - conspy_start) \
                      + ' seconds to run.')

        else:
            for read in reads:
              if 'CONSENS0' in read:
                out_cons_file = open(poa_cons, 'w')
                out_cons_file.write('>' + name + '\n' \
                                    + reads[read].replace('-', '') + '\n')
                out_cons_file.close()

        final = poa_cons
        for i in np.arange(1, 2, 1):
            try:
                if i == 1:
                    input_cons = poa_cons
                    output_cons = poa_cons.replace('.fasta', '_' + str(i) + '.fasta')
                else:
                    input_cons = poa_cons.replace('.fasta', '_' + str(i-1) + '.fasta')
                    output_cons = poa_cons.replace('.fasta', '_' + str(i) + '.fasta')
                mm_start = time()
                os.system('%s --secondary=no -ax map-ont \
                          %s %s > %s 2> ./minimap2_messages.txt' \
                          %(minimap2, input_cons, out_Fq, overlap))
                mm_stop = time()
                if timer:
                    print('minimap2 took ' + str(mm_stop - mm_start) \
                          + ' seconds to run.')

                racon_start = time()
                os.system('%s -q 5 -t 1 \
                          %s %s %s >%s 2>./racon_messages.txt' \
                          %(racon, out_Fq, overlap, input_cons, output_cons))
                racon_stop = time()
                if timer:
                    print('Racon took ' + str(racon_stop - racon_start) \
                          + ' seconds to run.')
                final = output_cons
            except:
                pass
        print(final)
        reads = read_fasta(final)
        for read in reads:
            corrected_consensus = reads[read]

    # reads that have the potential for a partial consensus
    elif len(peaks) == 1:
        # before/after positions are the alignment start/end positions for
        # both portions of the sequence
        beforeIndeces, afterIndeces = water_parser()
        endPortion = seq[beforeIndeces[1]:seed]
        begPortion = seq[seed:afterIndeces[0]]

        # make a temporary FASTQ file for consensus.py with portions
        # of reads that match itself
        tempFastqName = temp_folder + '/' + name + 'consensusFastq.fastq'
        tempFastq = open(tempFastqName, 'w+')
        tempFastq.write('@' + name + '\n'
                        + seq[beforeIndeces[0]:beforeIndeces[1] + 1] + '\n+\n'
                        + qual[beforeIndeces[0]:beforeIndeces[1] + 1] + '\n'
                        + '@' + name + '\n'
                        + seq[afterIndeces[0]:afterIndeces[1] + 1] + '\n+\n'
                        + qual[afterIndeces[0]:afterIndeces[1] + 1])
        tempFastq.close()
        alignedFasta = temp_folder + '/partial.fasta'
        fromConsensus = temp_folder + '/' + name + '_fromConsensus.fasta'
        zero_cons_start = time()
        os.system('%s %s %s > %s'
                  %(consensus, alignedFasta, tempFastqName, fromConsensus))
        zero_cons_stop = time()
        if timer:
            print('Zero repeat consensus.py took ' \
                  + str(zero_cons_stop - zero_cons_start) \
                  + ' seconds to run.')
        toGetConsensus = read_fasta(fromConsensus)
        seqFromCons = toGetConsensus['consensus']
        # put all the pieces back together to make the consensus
        corrected_consensus = begPortion + seqFromCons + endPortion
        repeats = '0'

    return corrected_consensus, repeats

def makeFigPartial(scoreList, peakList, seed, filtered_peaks):
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import matplotlib.patches as mplpatches
    plt.figure(figsize = (10, 5))
    hist = plt.axes([0.1, 0.1, 8/10, 4/5], frameon = True)

    xlist = [x for x in range(0, len(filtered_peaks))]
    hist.plot(xlist, filtered_peaks, color =  (0, 68/255, 85/255), \
              lw = 1, zorder = 5000)

    ylim = max(scoreList) * 1.1
    ymin = 0
    xlim = len(scoreList)

    for i in range(xlim):
        if np.in1d(i, peakList):
            color = (0.3, 0.3, 0.3)
            peakMark = mplpatches.Rectangle((i-12.5, filtered_peaks[i]), 25, ylim, \
                                            lw = 0, fc = (0.96, 0.43, 0.2), zorder = 0)
            hist.add_patch(peakMark) # 253/255, 177/255, 85/255
        else:
            scoreVal = mplpatches.Rectangle((i, 0), 3, scoreList[i], lw = 0, \
                                            facecolor = (0, 191/255, 165/255), zorder = 100)
            hist.add_patch(scoreVal)

    hist.set_ylim(ymin, ylim)
    hist.set_xlim(0, xlim)
    hist.set_xticks(range(0, xlim, 50))
    hist.set_xticklabels(range(0, xlim, 50), fontsize=4, rotation=90)
    hist.set_ylabel('Alignment Score', fontsize = 11, labelpad = 6.5)
    hist.set_xlabel('Read position', fontsize = 11, labelpad = 6)
    hist.tick_params(axis='both',which='both',\
                     bottom='on', labelbottom='on',\
                     left='on', labelleft='on',\
                     right='off', labelright='off',\
                     top='off', labeltop='off')
    plt.savefig('peakTest.png', dpi = 600)
    plt.close()
    sys.exit()

# def read_fastq_file(seq_file):
#     '''
#     Takes a FASTQ file and returns a list of tuples
#     In each tuple:
#         name : str, read ID
#         seed : int, first occurrence of the splint
#         seq : str, sequence
#         qual : str, quality line
#         average_quals : float, average quality of that line
#         seq_length : int, length of the sequence
#     '''
#     read_list, lineNum = [], 0
#     lastPlus = False
#     for line in open(seq_file):
#         line = line.rstrip()
#         if not line:
#             continue
#         # make an entry as a list and append the header to that list
#         if lineNum % 4 == 0 and line[0] == '@':
#             splitLine = line[1:].split('_')
#             root, seed = splitLine[0], 40
#             read_list.append([])
#             read_list[-1].append(root)
#             read_list[-1].append(seed)

#         # sequence
#         if lineNum % 4 == 1:
#             read_list[-1].append(line)

#         # quality header
#         if lineNum % 4 == 2:
#             lastPlus = True

#         # quality
#         if lineNum % 4 == 3 and lastPlus:
#             read_list[-1].append(line)
#             avgQ = sum([ord(x)-33 for x in line])/len(line)
#             read_list[-1].append(avgQ)
#             read_list[-1].append(len(read_list[-1][2]))
#             read_list[-1] = tuple(read_list[-1])

#         lineNum += 1
#     return read_list

def read_fastq_file(seq_file):
    '''
    Takes a FASTQ file and returns a list of tuples
    In each tuple:
        name : str, read ID
        seed : int, first occurrence of the splint
        seq : str, sequence
        qual : str, quality line
        average_quals : float, average quality of that line
        seq_length : int, length of the sequence
    '''
    read_list, lineNum = [], 0
    lastPlus = False
    for line in open(seq_file):
        line = line.rstrip()
        if not line:
            continue
        # make an entry as a list and append the header to that list
        if lineNum % 4 == 0 and line[0] == '@':
            splitLine = line[1:].split(' ')
            root, seed = splitLine[0], 40
            read_list.append([])
            read_list[-1].append(root)
            read_list[-1].append(seed)

        # sequence
        if lineNum % 4 == 1:
            read_list[-1].append(line)

        # quality header
        if lineNum % 4 == 2:
            lastPlus = True

        # quality
        if lineNum % 4 == 3 and lastPlus:
            read_list[-1].append(line)
            avgQ = sum([ord(x)-33 for x in line])/len(line)
            read_list[-1].append(avgQ)
            read_list[-1].append(len(read_list[-1][2]))
            read_list[-1] = tuple(read_list[-1])

        lineNum += 1
    return read_list

def analyze_reads(read_list):
    '''
    Takes reads that are longer than 1000 bases and gives the consensus.
    Writes to R2C2_Consensus.fasta
    '''
    for name, seed, seq, qual, average_quals, seq_length in read_list:
        if seqLenCutoff < seq_length:
            final_consensus = ''
            # score lists are made for sequence before and after the seed
            forward = seq[seed:]
            score_list_f = split_SW(name, forward, step=True)
            reverse = revComp(seq[:seed])
            score_list_r = split_SW(name, reverse, step=True)
            # calculate where peaks are and the median distance between them
            peaks, median_distance = callPeaks(score_list_f, score_list_r, seed)

            if len(peaks) == 1:
                scoreList = split_SW(name, seq, step=False)
                slr = []
                peaks, median_distance = callPeaks(scoreList, slr, seed)
                if len(peaks) == 2:
                    peaks.remove(seed)
                else:
                    continue

            if figure and len(peaks) > 1:
                makeFig(score_list_f, score_list_r, peaks, seed, median_distance)
            if figure and len(peaks) == 1:
                makeFigPartial(scoreList, peaks, seed, median_distance)

            final_consensus, repeats1 = determine_consensus(name, seq, peaks, \
                                                            qual, median_distance, \
                                                            seed)
            if final_consensus:
                final_out = open(out_file, 'a')
                final_out.write('>' + name + '_' \
                                + str(round(average_quals, 2)) + '_' \
                                + str(seq_length) + '_' + str(repeats1) \
                                + '_' + str(len(final_consensus)))
                final_out.write('\n' + final_consensus + '\n')
                final_out.close()
                os.system('rm ' + temp_folder + '/*')

# def analyze_reads(read_list):
#     '''
#     Takes reads that are longer than 1000 bases and gives the consensus.
#     Writes to R2C2_Consensus.fasta
#     '''
#     for name, seed, seq, qual, average_quals, seq_length in read_list:
#         if seqLenCutoff < seq_length:
#             final_consensus = ''
#             # score lists are made for sequence before and after the seed
#             forward = seq[seed:]
#             score_list_f = split_SW(name, forward, step=True)
#             reverse = revComp(seq[:seed])
#             score_list_r = split_SW(name, reverse, step=True)
#             # calculate where peaks are and the median distance between them
#             peaks, median_distance = callPeaks(score_list_f, score_list_r, seed)

#             if len(peaks) == 1:
#                 scoreList = split_SW(name, seq, step=False)
#                 slr = []
#                 peaks, median_distance = callPeaks(scoreList, slr, seed)
#                 if len(peaks) == 2:
#                     peaks.remove(seed)
#                 else:
#                     continue

#             if figure and len(peaks) > 1:
#                 makeFig(score_list_f, score_list_r, peaks, seed, median_distance)
#             if figure and len(peaks) == 1:
#                 makeFigPartial(scoreList, peaks, seed, median_distance)

#             final_consensus, repeats1 = determine_consensus(name, seq, peaks, \
#                                                             qual, median_distance, \
#                                                             seed)
#             if final_consensus:
#                 final_out = open(out_file, 'a')
#                 final_out.write('>' + name + '_' \
#                                 + str(round(average_quals, 2)) + '_' \
#                                 + str(seq_length) + '_' + str(repeats1) \
#                                 + '_' + str(len(final_consensus)))
#                 final_out.write('\n' + final_consensus + '\n')
#                 final_out.close()
#                 os.system('rm ' + temp_folder+'/*')

def main():
    '''Controls the flow of the program'''
    final_out = open(out_file, 'w')
    final_out.close()
    print(input_file)
    read_list = read_fastq_file(input_file)
    analyze_reads(read_list)

if __name__ == '__main__':
    main()

