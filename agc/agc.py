#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""OTU clustering"""

import argparse
import sys
import os
import gzip
import statistics
import textwrap
from pathlib import Path
from collections import Counter
from typing import Iterator, Dict, List
# https://github.com/briney/nwalign3
# ftp://ftp.ncbi.nih.gov/blast/matrices/
import nwalign3 as nw

__author__ = "Your Name"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Your Name"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Your Name"
__email__ = "your@email.fr"
__status__ = "Developpement"


def isfile(path: str) -> Path:  # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file

    :raises ArgumentTypeError: If file does not exist

    :return: (Path) Path object of the input file
    """
    myfile = Path(path)
    if not myfile.is_file():
        if myfile.is_dir():
            msg = f"{myfile.name} is a directory."
        else:
            msg = f"{myfile.name} does not exist."
        raise argparse.ArgumentTypeError(msg)
    return myfile


def get_arguments(): # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', '-amplicon_file', dest='amplicon_file', type=isfile, required=True, 
                        help="Amplicon is a compressed fasta file (.fasta.gz)")
    parser.add_argument('-s', '-minseqlen', dest='minseqlen', type=int, default = 400,
                        help="Minimum sequence length for dereplication (default 400)")
    parser.add_argument('-m', '-mincount', dest='mincount', type=int, default = 10,
                        help="Minimum count for dereplication  (default 10)")
    parser.add_argument('-o', '-output_file', dest='output_file', type=Path,
                        default=Path("OTU.fasta"), help="Output file")
    return parser.parse_args()


def read_fasta(amplicon_file: str, minseqlen: int) -> Iterator[str]:
    """
    Lit un fichier fasta.gz et retourne un générateur de séquences 
    dont la longueur est supérieure ou égale à minseqlen.

    :param amplicon_file: (str) Chemin vers le fichier fasta compressé (.gz)
    :param minseqlen: (int) Longueur minimale des séquences
    :yield: Séquences ayant une longueur >= minseqlen
    """
    with gzip.open(amplicon_file, 'rt') as f:
        sequence = ""
        for line in f:
            if line.startswith(">"):
                if len(sequence) >= minseqlen:
                    yield sequence
                sequence = ""
            else:
                sequence += line.strip()
        yield sequence
         

def dereplication_fulllength(amplicon_file: Path, minseqlen: int, mincount: int) -> Iterator[List]:
    """Dereplicate the set of sequence

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length
    :param mincount: (int) Minimum amplicon count
    :return: A generator object that provides a (list)[sequences, count] of sequence with a count >= mincount and a length >= minseqlen.
    """
    list_read = []
    
    sequences = list(read_fasta(amplicon_file, minseqlen))
    sequence_counts = Counter(sequences)
    
    for sequence, count in sequence_counts.most_common():
        if count >= mincount:
            yield [sequence, count]
    

def get_identity(alignment_list: List[str]) -> float:
    """Compute the identity rate between two sequences

    :param alignment_list:  (list) A list of aligned sequences in the format ["SE-QUENCE1", "SE-QUENCE2"]
    :return: (float) The rate of identity between the two sequences.
    """
    length_align = len(alignment_list[0])
    
    id_nucleotid = [x for x in range(length_align) if alignment_list[0][x]==alignment_list[1][x]]
    nb_id_nucleotid = len(id_nucleotid)
    
    return (nb_id_nucleotid/length_align)*100


def abundance_greedy_clustering(amplicon_file: Path, minseqlen: int, mincount: int, chunk_size: int, kmer_size: int) -> List:
    """Compute an abundance greedy clustering regarding sequence count and identity.
    Identify OTU sequences.

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length.
    :param mincount: (int) Minimum amplicon count.
    :param chunk_size: (int) A fournir mais non utilise cette annee
    :param kmer_size: (int) A fournir mais non utilise cette annee
    :return: (list) A list of all the [OTU (str), count (int)] .
    """
    seq_count = list(dereplication_fulllength(amplicon_file, minseqlen, mincount))
    
    list_OTU = [seq_count[0]]
    for seq in seq_count[1:]:
        flag = True
        for seq_OTU in list_OTU:
            align = nw.global_align(seq_OTU[0], seq[0], gap_open=-1, gap_extend=-1, matrix=str(Path(__file__).parent / "MATCH"))
            if get_identity(align) >= 97.0:
                flag = False
                break
        if flag:      
            list_OTU.append(seq)
    return list_OTU
    

def write_OTU(OTU_list: List, output_file: Path) -> None:
    """Write the OTU sequence in fasta format.

    :param OTU_list: (list) A list of OTU sequences
    :param output_file: (Path) Path to the output file
    """
    with open(output_file, "w") as output:
        for count, otu_seq in enumerate(OTU_list):
            seq, count_OTU = otu_seq
            output.write(f">OTU_{count+1} occurrence:{count_OTU}\n")
            output.write(textwrap.fill(seq, width=80)+"\n")
    # with open(output_file, "w") as file_write:
    #     counter = 1
    #     for element in OTU_list:
    #         file_write.write(f">OTU_{counter} occurrence:{element[1]}\n")
    #         for i in range(0, len(element[0]), 80):
    #             file_write.write(f"{element[0][i:i+80]}\n")
    #         counter += 1


#==============================================================
# Main program
#==============================================================
def main(): # pragma: no cover
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()
    list_OTU = abundance_greedy_clustering(args.amplicon_file, args.minseqlen, args.mincount, 0, 0)
    write_OTU(list_OTU, args.output_file)


if __name__ == '__main__':
    main()
