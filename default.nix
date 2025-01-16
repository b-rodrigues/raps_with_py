let
 pkgs = import (fetchTarball "https://github.com/rstats-on-nix/nixpkgs/archive/2025-01-14.tar.gz") {};
 rpkgs = builtins.attrValues {
  inherit (pkgs.rPackages) quarto ggplot2 knitr reticulate rmarkdown withr;
 };
 pypkgs = builtins.attrValues {
   inherit (pkgs.python312Packages) plotnine beautifulsoup4 polars requests xlsx2csv lxml pyarrow;
 };
 tex = (pkgs.texlive.combine {
   inherit (pkgs.texlive) scheme-small amsmath framed fvextra environ fontawesome5 orcidlink pdfcol tcolorbox tikzfill;
  });
 system_packages = builtins.attrValues {
  inherit (pkgs) R glibcLocalesUtf8 quarto python312;
};
  in
  pkgs.mkShell {
    LOCALE_ARCHIVE = if pkgs.system == "x86_64-linux" then  "${pkgs.glibcLocalesUtf8}/lib/locale/locale-archive" else "";
    LANG = "en_US.UTF-8";
    LC_ALL = "en_US.UTF-8";
    LC_TIME = "en_US.UTF-8";
    LC_MONETARY = "en_US.UTF-8";
    LC_PAPER = "en_US.UTF-8";
    LC_MEASUREMENT = "en_US.UTF-8";

    buildInputs = [ pypkgs rpkgs tex system_packages  ];
      
  }
