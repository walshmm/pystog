#!/usr/bin/env python
import json
import numpy as np
import pandas as pd
import argparse
import matplotlib.pyplot as plt

from transformer import Converter, Transformer, FourierFilter
from transformer import RealSpaceChoices, ReciprocalSpaceChoices


def parser_cli_args(args):
    # Get each file's info and story in dictionary
    files_info = list() 
    for f in args.filenames:
        file_info = dict()
        file_info["Filename"] = f[0]
        file_info["Qmin"] = float(f[1])
        file_info["Qmax"] = float(f[2])
        file_info["Y"] = { "Offset" : float(f[3]), "Scale" : float(f[4]) }
        file_info["X"] = { "Offset" : float(f[5]) }
        file_info["ReciprocalFunction"] = f[6]
        files_info.append(file_info)

    # Get general StoG options
    kwargs = {  "Files" : files_info,
                "NumberDensity" : args.density,
                "Rmax" : args.Rmax,
                "Rpoints" : args.Rpoints, 
                "FourierFilter" : { "Cutoff" : args.fourier_filter_cutoff},
                "LorchFlag" : args.lorch_flag, 
                "PlotFlag" : args.plot, 
                "Outputs" : { "StemName" : args.stem_name },
                "Merging" : {"Y" : {"Offset" : args.merging[0], "Scale" : args.merging[1]} },
                "<b_coh>^2" : args.bcoh_sqrd,
                "<b_tot^2>" : args.btot_sqrd,
                "RealSpaceFunction" : args.real_space_function,
    }
    if args.Rdelta:
        kwargs["Rdelta"] = args.Rdelta

    return kwargs



class PyStoG(object):

    def __init__(self, **kwargs):
        self.df_individuals = pd.DataFrame()

        self.df_sq_master = pd.DataFrame()
        self.sq_title = "S(Q) Merged"
        self.ft_title = "FT term"
        self.sq_ft_title = "S(Q) FT"
        self.fq_rmc_title = "F(Q) RMC"

        if "RealSpaceFunction" in kwargs:
            self.real_space_function = str(kwargs["RealSpaceFunction"])
        else:
            self.real_space_function = "g(r)"

        self.df_gr_master = pd.DataFrame()
        self.gr_ft_title = "%s FT" % self.real_space_function
        self.dr_ft_title = "D(r) FT"
        self.gr_lorch_title = "%s FT Lorched" % self.real_space_function
        self.gr_title = "%s Merged" % self.real_space_function
        self.gr_rmc_title = "G(r) RMC"

        self.files = kwargs["Files"]
        self.xmin = 100
        self.xmax = 0

        self.dr = None

        self.density = kwargs["NumberDensity"]
        self.stem_name = kwargs["Outputs"]["StemName"]
        self.Rmax = float(kwargs["Rmax"])
        self.Rdelta = self.Rmax / kwargs["Rpoints"]
        if "FourierFilter" in kwargs:
            self.fourier_filter_cutoff = kwargs["FourierFilter"]["Cutoff"]
        if "Rdelta" in kwargs:
            self.Rdelta = kwargs["Rdelta"]
        self.lorch_flag = kwargs["LorchFlag"]
        self.plot_flag = kwargs["PlotFlag"]
        self.bcoh_sqrd = kwargs["<b_coh>^2"]
        if "<b_tot^2>" in kwargs:
            self.btot_sqrd = kwargs["<b_tot^2>"]

        if "Merging" in kwargs:
            self.merging = kwargs["Merging"]
        else:
            self.merging = {"Y" : {"Offset" : 0.0, "Scale" : 1.0} }


        self.converter = Converter()
        self.transformer = Transformer()
        self.filter = FourierFilter()

    # -------------------------------------#
    # Reading and Merging Spectrum

    def read_all_data(self, **kwargs):
        if len(self.files) == 0:
            print("No files loaded for PyStog")
            return

        for i, file_info in enumerate(self.files):
            file_info['index'] = i
            self.read_dataset(file_info, **kwargs)
        return

    def read_dataset(self, info, xcol=0, ycol=1, sep=r"\s*", **kwargs):
        data = pd.read_csv(info['Filename'],
                           sep=sep,
                           usecols=[xcol, ycol],
                           names=['x', 'y'],
                           engine='python',
                           **kwargs)
        info['data'] = data
        data = self.add_dataset(info, **kwargs)
        return data

    def add_dataset(self, info, decimals=4, **kwargs):
        x = np.array(info['data']['x'])
        y = np.array(info['data']['y'])

        x, y = self.transformer.apply_cropping(x, y, info['Qmin'], info['Qmax'])
        x, y = self.apply_scales_and_offset(x, y, 
                                            info['Y']['Scale'], 
                                            info['Y']['Offset'], 
                                            info['X']['Offset'])

        if info["ReciprocalFunction"] == "F(Q)":
            y = self.converter.F_to_S(x, y)
        elif info["ReciprocalFunction"] == "FK(Q)":
            y = self.converter.FK_to_S(x, y, **{'<b_coh>^2' : self.bcoh_sqrd} )
        elif info["ReciprocalFunction"] == "DCS(Q)":
            y = self.converter.DCS_to_S(x, y, **{'<b_coh>^2' : self.bcoh_sqrd, '<b_tot^2>' : self.btot_sqrd} )
        self.xmin = min(self.xmin, min(x))
        self.xmax = max(self.xmax, max(x))
        df = pd.DataFrame(y, columns=['S(Q)_%d' % info['index']], index=x)
        self.df_individuals = pd.concat([self.df_individuals, df], axis=1)
        return df

    def apply_scales_and_offset(self, x, y, yscale, yoffset, xoffset):
        y = self.scale(y, yscale)
        y = self.offset(y, yoffset)
        x = self.offset(x, xoffset)
        return x, y

    def merge_data(self):
        # Sum over single S(Q) columns into a merged S(Q)
        self.df_sq_master[self.sq_title] = self.df_individuals.iloc[:, :].mean(
            axis=1)

        x = self.df_sq_master[self.sq_title].index.values
        y = self.df_sq_master[self.sq_title].values

        x, y = self.apply_scales_and_offset(x, y, 
                                     self.merging['Y']['Scale'],
                                     self.merging['Y']['Offset'],
                                     0.0)

        self.df_sq_master[self.sq_title] = y
        
        return

    def offset(self, data, offset):
        data = data + offset
        return data

    def scale(self, data, scale):
        data = scale * data
        return data

    # -------------------------------------#
    # Transform Utilities

    def create_dr(self):
        self.dr = np.arange(self.Rdelta, self.Rmax + self.Rdelta, self.Rdelta)

    '''
    def bit_merged(self):
        self.bit( self.df_sq_master, self.sq_title, lorch=False)

    def bit(self, df, col_name, **kwargs):
        if self.dr is None:
            self.create_dr()

        q = df.index.values
        sofq = df[col_name].values

        kwargs['df'] = df
        r, gofr = self.transform(q, sofq, self.dr, **kwargs)

        self.df_gr_master[self.gr_title] = gofr
        self.df_gr_master = self.df_gr_master.set_index(r)
    '''

    def qmin_correction(self, q, sofq, dr, gofr, lorch):
        qmin = min(q)
        qmax = max(q)
        sofq_qmin = sofq[0]
        PiOverQmax = np.pi / qmax

        correction = np.zeros_like(gofr)
        for i, r in enumerate(dr):
            v = qmin * r
            if lorch:
                vm = qmin * (r - PiOverQmax)
                vp = qmin * (r + PiOverQmax)
                term1 = (vm * np.sin(vm) + np.cos(vm) - 1.) / \
                    (r - PiOverQmax)**2.
                term2 = (vp * np.sin(vp) + np.cos(vp) - 1.) / \
                    (r + PiOverQmax)**2.
                F1 = (term1 - term2) / (2. * PiOverQmax)
                F2 = (np.sin(vm) / (r - PiOverQmax) - np.sin(vp) / \
                    (r + PiOverQmax) )/ (2. * PiOverQmax)
            else:
                F1 = (2. * v * np.sin(v) - (v * v - 2.) *
                      np.cos(v) - 2.) / r / r / r
                F2 = (np.sin(v) - v * np.cos(v)) / r / r

            correction[i] = (2 / np.pi) * (F1 * sofq_qmin / qmin - F2)
        gofr += correction
    
        self._omitted_correction = correction

        return gofr

    def fourier_filter(self):
        kwargs = {'lorch' : False, 'rho' : self.density}
        cutoff = self.fourier_filter_cutoff

        # Get reciprocal and real space data
        r  = self.df_gr_master[self.gr_title].index.values
        gr = self.df_gr_master[self.gr_title].values
        q = self.df_sq_master[self.sq_title].index.values
        sq = self.df_sq_master[self.sq_title].values

        # Fourier filter g(r)
        if self.real_space_function == "g(r)":
            q_ft, sq_ft, q, sq, r, gr = self.filter.g_using_S(r, gr, q, sq, cutoff, **kwargs)
        elif self.real_space_function == "G(r)":
            q_ft, sq_ft, q, sq, r, gr = self.filter.G_using_S(r, gr, q, sq, cutoff, **kwargs)
        elif self.real_space_function == "GK(r)":
            q_ft, sq_ft, q, sq, r, gr = self.filter.GK_using_S(r, gr, q, sq, cutoff, **kwargs)
        else:
            raise Exception("ERROR: Unknown real space function %s" % self.real_space_function)

        # Add output to master dataframes and write files
        self.df_sq_master = self.add_to_dataframe(q_ft,sq_ft,self.df_sq_master,self.ft_title)
        self.write_out_ft()

        self.df_sq_master = self.add_to_dataframe(q, sq, self.df_sq_master, self.sq_ft_title)
        self.write_out_ft_sq()

        self.df_gr_master = self.add_to_dataframe(r, gr, self.df_gr_master, self.gr_ft_title)
        self.write_out_ft_gr()

        # Plot results
        if self.plot_flag:
            df_sq = self.df_sq_master.ix[ :, self.df_sq_master.columns.difference([self.sq_ft_title]) ]
            self.plot_sq(df_sq, ylabel="FourierFilter(Q)", 
                         title="Fourier Transform of the filtered low-r region below cutoff")
            self.plot_sq(self.df_sq_master, title="Fourier Filtered S(Q)")
            self.plot_gr(self.df_gr_master, title="Fourier Filtered %s" % self.real_space_function)

        return q, sq, r, gr
        
    def apply_lorch(self,q,sq,r):
        if self.real_space_function == "g(r)":
            r, gr_lorch = self.transformer.S_to_g(q, sq, r, **{'lorch' : True, 'rho' : self.density} )
        elif self.real_space_function == "G(r)":
            r, gr_lorch = self.transformer.S_to_G(q, sq, r, **{'lorch' : True} )
        elif self.real_space_function == "GK(r)":
            r, gr_lorch = self.transformer.S_to_GK(q, sq, r, **{'lorch' : True, 'rho' : self.density} )
        else:
            raise Exception("ERROR: Unknown real space function %s" % self.real_space_function)

        self.df_gr_master = self.add_to_dataframe(r, gr_lorch, 
                                                  self.df_gr_master, self.gr_lorch_title)
        self.write_out_lorched_gr()

        if self.plot_flag:
            self.plot_gr(self.df_gr_master, title="Lorched %s" % self.real_space_function)
            plt.show()

        return r, gr_lorch

    def get_lowR_mean_square(self):
        gofr = self.df_gr_master[self.gr_title].values
        return self.lowR_mean_square(self.dr, gofr)

    def lowR_mean_square(self, dr, gofr, limit=1.01):
        gofr = gofr[dr <= limit]
        gofr_sq = np.multiply(gofr, gofr)
        average = sum(gofr_sq)
        return np.sqrt(average)

    def add_keen_fq(self,q,sq):
        fq_rmc = self.bcoh_sqrd*(sq-1)
        self.df_sq_master = self.add_to_dataframe(q, fq_rmc, self.df_sq_master, self.fq_rmc_title)
        self.write_out_rmc_fq()

    def add_keen_gr(self, r, gr_out):
        gr_rmc = self.bcoh_sqrd*(gr_out-1)
        self.df_gr_master = self.add_to_dataframe(r, gr_rmc, self.df_gr_master, self.gr_rmc_title)
        self.write_out_rmc_gr()
 
    # -------------------------------------#
    # Plot Utilities

    def plot_sq(self, df, xlabel='Q', ylabel='S(Q)', title=''):
        df.plot()
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.show()

    def plot_gr(self, df, xlabel='r', ylabel='G(r)', title=''):
        df.plot()
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.show()


    def plot_merged_sq(self):
        fig, (ax1, ax2) = plt.subplots(1, 2,sharey=True)
        self.df_individuals.plot(ax=ax1)
        self.df_sq_master.plot(ax=ax2)
        plt.xlabel("Q")
        plt.ylabel("S(Q)")
        ax1.set_title("Individual S(Q)")
        ax2.set_title("Merged S(Q)")
        plt.show()

    def plot_summary_sq(self):
        fig, (ax1, ax2) = plt.subplots(1, 2,sharey=True)
        df_sq = self.df_sq_master.ix[ :, self.df_sq_master.columns.difference([self.fq_rmc_title]) ]
        df_sq.plot(ax=ax1)
        df_fq = self.df_sq_master.ix[ :, [self.fq_rmc_title] ]
        df_fq.plot(ax=ax2)
        plt.xlabel("Q")
        ax1.set_ylabel("S(Q)")
        ax1.set_title("StoG S(Q) functions")
        ax2.set_ylabel("FK(Q)")
        ax2.set_title("Keen's F(Q)")
        plt.show()

    def plot_summary_gr(self):
        fig, (ax1, ax2) = plt.subplots(1, 2,sharey=True)
        df_gr = self.df_gr_master.ix[ :, self.df_gr_master.columns.difference([self.gr_rmc_title]) ]
        df_gr.plot(ax=ax1)
        df_gk = self.df_gr_master.ix[ :, [self.gr_rmc_title] ]
        df_gk.plot(ax=ax2)
        plt.xlabel("r")
        ax1.set_ylabel(self.real_space_function)
        ax1.set_title("StoG %s functions" % self.real_space_function)
        ax2.set_ylabel("GK(r)")
        ax2.set_title("Keen's G(r)")
        plt.show()

    # -------------------------------------#
    # Output Utilities

    def add_to_dataframe(self,x,y,df,title):
        df_temp = pd.DataFrame(y, columns=[title], index=x)
        df = pd.concat([df, df_temp], axis=1)
        return df
        
    def write_out_df(self, df, cols, filename):
        if df.empty:
            print("Empty dataframe.")
            return
        with open(filename, 'w') as f:
            f.write("%d \n" % df.shape[0])
            f.write("# Comment line\n")
        with open(filename, 'a') as f:
            df.to_csv(f, sep='\t', columns=cols, header=False)

    def write_out_merged_sq(self, filename=None):
        if filename is None:
            filename = "%s.sq" % self.stem_name
        self.write_out_df(self.df_sq_master, [self.sq_title], filename)

    def write_out_merged_gr(self, filename=None):
        if filename is None:
            filename = "%s.gr" % self.stem_name
        self.write_out_df(self.df_gr_master, [self.gr_title], filename)

    def write_out_ft(self, filename=None):
        if filename is None:
            filename = "ft.dat"
        self.write_out_df(self.df_sq_master, [self.ft_title], filename)

    def write_out_ft_sq(self, filename=None):
        if filename is None:
            filename = "%s_ft.sq" % self.stem_name
        self.write_out_df(self.df_sq_master, [self.sq_ft_title], filename)

    def write_out_ft_gr(self, filename=None):
        if filename is None:
            filename = "%s_ft.gr" % self.stem_name
        self.write_out_df(self.df_gr_master, [self.gr_ft_title], filename)

    def write_out_ft_dr(self, filename=None):
        if filename is None:
            filename = "%s_ft.dr" % self.stem_name
        self.write_out_df(self.df_gr_master, [self.dr_ft_title], filename)

    def write_out_lorched_gr(self, filename=None):
        if filename is None:
            filename = "%s_ft_lorched.gr" % self.stem_name
        self.write_out_df(self.df_gr_master, [self.gr_lorch_title], filename)

    def write_out_rmc_fq(self, filename=None):
        if filename is None:
            filename = "%s_rmc.fq" % self.stem_name
        self.write_out_df(self.df_sq_master, [self.fq_rmc_title], filename)

    def write_out_rmc_gr(self, filename=None):
        if filename is None:
            filename = "%s_rmc.gr" % self.stem_name
        self.write_out_df(self.df_gr_master, [self.gr_rmc_title], filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=str, default=None,
                        help="Read JSON input file for arguments")
    parser.add_argument("--density", type=float,
                        help="Number density (atoms/angstroms^3")
    parser.add_argument("-f", "--filename", nargs='*', action='append',
                        default=list(), dest='filenames',
                        help="Filename, qmin, qmax, yoffset, yscale, Q offset, function type."+
                             "Function Types are: %s" % json.dumps(ReciprocalSpaceChoices))
    parser.add_argument(
        "--stem-name",
        type=str,
        dest="stem_name",
        default="merged",
        help="Stem name for output files")
    parser.add_argument(
        "--Rmax",
        type=float,
        default=50.0,
        help="Maximum value in angstroms for real-space functions")
    parser.add_argument("--real-space-function", type=str, default="g(r)", dest="real_space_function",
                        help="Real-space function typej. Choices are: %s" % json.dumps(RealSpaceChoices))
    parser.add_argument("--Rpoints", type=int, default=5000,
                        help="Number of points in R for real-space functions")
    parser.add_argument("--Rdelta", type=float, default=None,
                        help="Bin width to use in R for real-space functions")
    parser.add_argument("--fourier-filter-cutoff", type=float,
                        default=None, dest="fourier_filter_cutoff",
                        help="Bin width to use in R for real-space functions")
    parser.add_argument("--lorch-flag", action="store_true",
                        default=False, dest="lorch_flag",
                        help="Apply Lorch function")
    parser.add_argument("--bcoh_sqrd", type=float, default=1.0, dest="bcoh_sqrd",
                        help="The (sum c*bbar)^2 term needed for F(Q) and G(r) for RMC output")
    parser.add_argument("--btot_sqrd", type=float, default=1.0, dest="btot_sqrd",
                        help="The (sum c*b^2) term needed for DCS(Q) input")
    parser.add_argument("--plot", action="store_true", default=False,
                        help="Plots using matplotlib along the way")
    parser.add_argument("--merging", nargs=2, type=float, default=[0.0,1.0],
                        help="Offset and Scale to apply to the merged S(Q)")
    args = parser.parse_args()

    
    if args.json:
        print("loading config from '%s'" % args.json)
        with open(args.json, 'r') as f:
            kwargs = json.load(f)


    else:
        kwargs = parser_cli_args(args)

    # Merge S(Q) files
    stog = PyStoG(**kwargs)
    stog.read_all_data(skiprows=3)
    stog.merge_data()
    stog.write_out_merged_sq()

    # Initialize S(Q)
    q    = stog.df_sq_master[stog.sq_title].index.values
    sofq = stog.df_sq_master[stog.sq_title].values

    if kwargs["PlotFlag"]:
        stog.plot_merged_sq()


    # Initial S(Q) -> g(r) transform 
    stog.create_dr()
    if stog.real_space_function == "g(r)":
        r, gofr = stog.transformer.S_to_g(q, sofq, stog.dr, **{'lorch' : False, 'rho' : stog.density} )
    elif stog.real_space_function == "G(r)":
        r, gofr = stog.transformer.S_to_G(q, sofq, stog.dr, **{'lorch' : False} )
    elif stog.real_space_function == "GK(r)":
        r, gofr = stog.transformer.S_to_GK(q, sofq, stog.dr, **{'lorch' : False, 'rho' : stog.density} )
    else:
        raise Exception("ERROR: Unknown real space function %s" % stog.real_space_function)

    stog.df_gr_master[stog.gr_title] = gofr
    stog.df_gr_master = stog.df_gr_master.set_index(r)
    stog.write_out_merged_gr()

    if kwargs["PlotFlag"]:
        stog.plot_gr(stog.df_gr_master, ylabel=stog.real_space_function, title="Merged %s" % stog.real_space_function)

    #print stog.get_lowR_mean_square()

    # Set the S(Q) and g(r) if no Fourier Filter
    sq = stog.df_sq_master[stog.sq_title].values
    gr_out = gofr

    # Apply Fourier Filter
    if "FourierFilter" in kwargs:
        q, sq, r, gr_out = stog.fourier_filter()

    # Apply Lorch Modification
    if kwargs["LorchFlag"]:
        r, gr_out = stog.apply_lorch(q,sq,r)

    # Apply final scale number
    stog.add_keen_fq(q,sq)
    stog.add_keen_gr(r,gr_out)
   
    if kwargs["PlotFlag"]:
        stog.plot_summary_sq()
        stog.plot_summary_gr()
