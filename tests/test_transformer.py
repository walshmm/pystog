import unittest
import numpy
from utils import \
    load_test_data, get_index_of_function, \
    REAL_HEADERS, RECIPROCAL_HEADERS
from materials import Nickel, Argon
from pystog.transformer import Transformer

# Real Space Function


class TestTransformerBase(unittest.TestCase):
    rtol = 0.2
    atol = 0.2

    def initialize_material(self):
        # setup input data
        self.kwargs = self.material.kwargs

        # setup the tolerance
        self.real_space_first = self.material.real_space_first
        self.real_space_last = self.material.real_space_last

        data = load_test_data(self.material.real_space_filename)
        self.r = data[:, get_index_of_function("r", REAL_HEADERS)]
        self.gofr = data[:, get_index_of_function("g(r)", REAL_HEADERS)]
        self.GofR = data[:, get_index_of_function("G(r)", REAL_HEADERS)]
        self.GKofR = data[:, get_index_of_function("GK(r)", REAL_HEADERS)]

        # targets for 1st peaks
        self.gofr_target = self.material.gofr_target
        self.GofR_target = self.material.GofR_target
        self.GKofR_target = self.material.GKofR_target

        # setup the tolerance
        self.reciprocal_space_first = self.material.reciprocal_space_first
        self.reciprocal_space_last = self.material.reciprocal_space_last

        data = load_test_data(self.material.reciprocal_space_filename)
        self.q = data[:, get_index_of_function("Q", RECIPROCAL_HEADERS)]
        self.sq = data[:, get_index_of_function("S(Q)", RECIPROCAL_HEADERS)]
        self.fq = data[:, get_index_of_function("F(Q)", RECIPROCAL_HEADERS)]
        self.fq_keen = data[:, get_index_of_function(
            "FK(Q)", RECIPROCAL_HEADERS)]
        self.dcs = data[:, get_index_of_function("DCS(Q)", RECIPROCAL_HEADERS)]

        # targets for 1st peaks
        self.sq_target = self.material.sq_target
        self.fq_target = self.material.fq_target
        self.fq_keen_target = self.material.fq_keen_target
        self.dcs_target = self.material.dcs_target

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.transformer = Transformer()

    def tearDown(self):
        unittest.TestCase.tearDown(self)

    # Utilities

    def test_extend_axis_to_low_end(self):
        xin = numpy.linspace(0.5, 1.0, 11)
        xout = self.transformer._extend_axis_to_low_end(xin)
        self.assertEqual(xout[0], 0.05)
        self.assertEqual(xout[-1], 1.0)

    def test_apply_cropping(self):
        xin = numpy.linspace(0.5, 1.0, 11)
        yin = numpy.linspace(4.5, 5.0, 11)
        x, y = self.transformer.apply_cropping(xin, yin, 0.6, 0.7)
        self.assertTrue(numpy.alltrue(x == [0.6, 0.65, 0.7]))
        self.assertTrue(numpy.alltrue(y == [4.6, 4.65, 4.7]))

    def test_fourier_transform(self):
        fs = 100  # sample rate
        f = 10  # the frequency of the signal
        # the points on the x axis for plotting
        xin = numpy.linspace(0.0, 100., 1000)
        yin = numpy.asarray(
            [numpy.sin(2 * numpy.pi * f * (i / fs)) for i in xin])
        xout = numpy.linspace(0.0, 2.0, 100)
        xout, yout = self.transformer.fourier_transform(xin, yin, xout)
        yout_target = [-6.99109862,
                       31.19080001113671,
                       48.394807800183614,
                       12.598301416877067,
                       -10.486717499230888]
        first = 28
        last = 33
        self.assertTrue(numpy.allclose(yout[first:last],
                                       yout_target,
                                       rtol=self.rtol, atol=self.atol))

    def test_fourier_transform_with_lorch(self):
        fs = 100  # sample rate
        f = 10  # the frequency of the signal
        # the points on the x axis for plotting
        xin = numpy.linspace(0.0, 100., 1000)
        yin = numpy.asarray(
            [numpy.sin(2 * numpy.pi * f * (i / fs)) for i in xin])
        xout = numpy.linspace(0.0, 2.0, 100)
        xout, yout = self.transformer.fourier_transform(xin, yin, xout, **{'lorch':True})
        yout_target = [7.36295491382,
                       23.3584279212,
                       29.0370190673,
                       16.889216949,
                       2.41130973148]
        first = 28
        last = 33
        self.assertTrue(numpy.allclose(yout[first:last],
                                       yout_target,
                                       rtol=self.rtol, atol=self.atol))

    def test_low_x_correction_with_lorch(self):
        fs = 100  # sample rate
        f = 10  # the frequency of the signal
        # the points on the x axis for plotting
        xin = numpy.linspace(0.0, 100., 1000)
        yin = numpy.asarray(
            [numpy.sin(2 * numpy.pi * f * (i / fs)) for i in xin])
        xout = numpy.linspace(0.0, 2.0, 100)
        xout, yout = self.transformer.fourier_transform(xin, yin, xout, **{'lorch':True})
        yout = self.transformer._low_x_correction(xin, yin, xout, yout, **{'lorch':True})
        yout_target = [7.36295491,
                       23.35842792,
                       29.03701907,
                       16.88921695,
                       2.41130973]
        first = 28
        last = 33
        self.assertTrue(numpy.allclose(yout[first:last],
                                       yout_target,
                                       rtol=self.rtol, atol=self.atol))

    # Real space

    # g(r) tests

    def g_to_S(self):
        q, sq = self.transformer.g_to_S(
            self.r, self.gofr, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(sq[first:last],
                                       self.sq_target,
                                       rtol=self.rtol, atol=self.atol))

    def g_to_F(self):
        q, fq = self.transformer.g_to_F(
            self.r, self.gofr, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(fq[first:last],
                                       self.fq_target,
                                       rtol=self.rtol, atol=self.atol))

    def g_to_FK(self):
        q, fq_keen = self.transformer.g_to_FK(
            self.r, self.gofr, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(fq_keen[first:last],
                                       self.fq_keen_target,
                                       rtol=self.rtol, atol=self.atol))

    def g_to_DCS(self):
        q, dcs = self.transformer.g_to_DCS(
            self.r, self.gofr, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(dcs[first:last],
                                       self.dcs_target,
                                       rtol=self.rtol, atol=self.atol))

    # G(r) tests
    def G_to_S(self):
        q, sq = self.transformer.G_to_S(
            self.r, self.GofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(sq[first:last],
                                       self.sq_target,
                                       rtol=self.rtol, atol=self.atol))

    def G_to_F(self):
        q, fq = self.transformer.G_to_F(
            self.r, self.GofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(fq[first:last],
                                       self.fq_target,
                                       rtol=self.rtol, atol=self.atol))

    def G_to_FK(self):
        q, fq_keen = self.transformer.G_to_FK(
            self.r, self.GofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(fq_keen[first:last],
                                       self.fq_keen_target,
                                       rtol=self.rtol, atol=self.atol))

    def G_to_DCS(self):
        q, dcs = self.transformer.G_to_DCS(
            self.r, self.GofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(dcs[first:last],
                                       self.dcs_target,
                                       rtol=self.rtol, atol=self.atol))
    # GK(r) tests

    def GK_to_S(self):
        q, sq = self.transformer.GK_to_S(
            self.r, self.GKofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(sq[first:last],
                                       self.sq_target,
                                       rtol=self.rtol, atol=self.atol))

    def GK_to_F(self):
        q, fq = self.transformer.GK_to_F(
            self.r, self.GKofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(fq[first:last],
                                       self.fq_target,
                                       rtol=self.rtol, atol=self.atol))

    def GK_to_FK(self):
        q, fq_keen = self.transformer.GK_to_FK(
            self.r, self.GKofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(fq_keen[first:last],
                                       self.fq_keen_target,
                                       rtol=self.rtol, atol=self.atol))

    def GK_to_DCS(self):
        q, dcs = self.transformer.GK_to_DCS(
            self.r, self.GKofR, self.q, **self.kwargs)
        first, last = self.reciprocal_space_first, self.reciprocal_space_last
        self.assertTrue(numpy.allclose(dcs[first:last],
                                       self.dcs_target,
                                       rtol=self.rtol, atol=self.atol))

    # Reciprocal space

    # S(Q) tests
    def S_to_g(self):
        r, gofr = self.transformer.S_to_g(
            self.q, self.sq, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(gofr[first:last],
                                       self.gofr_target,
                                       rtol=self.rtol, atol=self.atol))

    def S_to_G(self):
        r, GofR = self.transformer.S_to_G(
            self.q, self.sq, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GofR[first:last],
                                       self.GofR_target,
                                       rtol=self.rtol, atol=self.atol))

    def S_to_GK(self):
        r, GKofR = self.transformer.S_to_GK(
            self.q, self.sq, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GKofR[first:last],
                                       self.GKofR_target,
                                       rtol=self.rtol, atol=self.atol))
    # F(Q) tests

    def F_to_g(self):
        r, gofr = self.transformer.F_to_g(
            self.q, self.fq, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(gofr[first:last],
                                       self.gofr_target,
                                       rtol=self.rtol, atol=self.atol))

    def F_to_G(self):
        r, GofR = self.transformer.F_to_G(
            self.q, self.fq, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GofR[first:last],
                                       self.GofR_target,
                                       rtol=self.rtol, atol=self.atol))

    def F_to_GK(self):
        r, GKofR = self.transformer.F_to_GK(
            self.q, self.fq, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GKofR[first:last],
                                       self.GKofR_target,
                                       rtol=self.rtol, atol=self.atol))
    # FK(Q) tests

    def FK_to_g(self):
        r, gofr = self.transformer.FK_to_g(
            self.q, self.fq_keen, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(gofr[first:last],
                                       self.gofr_target,
                                       rtol=self.rtol, atol=self.atol))

    def FK_to_G(self):
        r, GofR = self.transformer.FK_to_G(
            self.q, self.fq_keen, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GofR[first:last],
                                       self.GofR_target,
                                       rtol=self.rtol, atol=self.atol))

    def FK_to_GK(self):
        r, GKofR = self.transformer.FK_to_GK(
            self.q, self.fq_keen, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GKofR[first:last],
                                       self.GKofR_target,
                                       rtol=self.rtol, atol=self.atol))
    # DCS(Q) tests

    def DCS_to_g(self):
        r, gofr = self.transformer.DCS_to_g(
            self.q, self.dcs, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(gofr[first:last],
                                       self.gofr_target,
                                       rtol=self.rtol, atol=self.atol))

    def DCS_to_G(self):
        r, GofR = self.transformer.DCS_to_G(
            self.q, self.dcs, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GofR[first:last],
                                       self.GofR_target,
                                       rtol=self.rtol, atol=self.atol))

    def DCS_to_GK(self):
        r, GKofR = self.transformer.DCS_to_GK(
            self.q, self.dcs, self.r, **self.kwargs)
        first, last = self.real_space_first, self.real_space_last
        self.assertTrue(numpy.allclose(GKofR[first:last],
                                       self.GKofR_target,
                                       rtol=self.rtol, atol=self.atol))


class TestTransformerNickel(TestTransformerBase):
    def setUp(self):
        super(TestTransformerNickel, self).setUp()
        self.material = Nickel()
        self.initialize_material()

    def test_g_to_S(self):
        self.g_to_S()

    def test_g_to_F(self):
        self.g_to_F()

    def test_g_to_FK(self):
        self.g_to_FK()

    def test_g_to_DCS(self):
        self.g_to_DCS()

    def test_G_to_S(self):
        self.G_to_S()

    def test_G_to_F(self):
        self.G_to_F()

    def test_G_to_FK(self):
        self.G_to_FK()

    def test_G_to_DCS(self):
        self.G_to_DCS()

    def test_GK_to_S(self):
        self.GK_to_S()

    def test_GK_to_F(self):
        self.GK_to_F()

    def test_GK_to_FK(self):
        self.GK_to_FK()

    def test_GK_to_DCS(self):
        self.GK_to_DCS()


class TestTransformerArgon(TestTransformerBase):
    def setUp(self):
        super(TestTransformerArgon, self).setUp()
        self.material = Argon()
        self.initialize_material()

    def test_g_to_S(self):
        self.g_to_S()

    def test_g_to_F(self):
        self.g_to_F()

    def test_g_to_FK(self):
        self.g_to_FK()

    def test_g_to_DCS(self):
        self.g_to_DCS()

    def test_G_to_S(self):
        self.G_to_S()

    def test_G_to_F(self):
        self.G_to_F()

    def test_G_to_FK(self):
        self.G_to_FK()

    def test_G_to_DCS(self):
        self.G_to_DCS()

    def test_GK_to_S(self):
        self.GK_to_S()

    def test_GK_to_F(self):
        self.GK_to_F()

    def test_GK_to_FK(self):
        self.GK_to_FK()

    def test_GK_to_DCS(self):
        self.GK_to_DCS()

    def test_S_to_g(self):
        self.S_to_g()

    def test_S_to_G(self):
        self.S_to_G()

    def test_S_to_GK(self):
        self.S_to_GK()

    def test_F_to_g(self):
        self.F_to_g()

    def test_F_to_G(self):
        self.F_to_G()

    def test_F_to_GK(self):
        self.F_to_GK()

    def test_FK_to_g(self):
        self.FK_to_g()

    def test_FK_to_G(self):
        self.FK_to_G()

    def test_FK_to_GK(self):
        self.FK_to_GK()

    def test_DCS_to_g(self):
        self.DCS_to_g()

    def test_DCS_to_G(self):
        self.DCS_to_G()

    def test_DCS_to_GK(self):
        self.DCS_to_GK()
