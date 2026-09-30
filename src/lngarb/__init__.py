"""US Gulf LNG destination arbitrage: netbacks to Northwest Europe and Northeast Asia.

The package prices a cargo loaded at Sabine Pass delivered into Northwest Europe
against TTF and into Northeast Asia against JKM, route by route, net of
liquefaction, freight, boil-off, canal costs and regasification.

    lngarb.units      the one conversion path between EUR/MWh and USD/MMBtu
    lngarb.config     every parameter and source the study declares
    lngarb.sources    one adapter per data source, and the shared plumbing
"""
