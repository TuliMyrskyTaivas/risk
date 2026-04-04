from fpdf import FPDF
from datetime import datetime
from pandas import DataFrame

class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        # Use Windows built-in fonts
        # Path to Windows Fonts folder
        windows_fonts = "C:/Windows/Fonts/"
        
        # Try different Windows Unicode fonts
        try:
            # Arial Unicode MS (if installed) - best Unicode support
            self.add_font('ArialUnicode', '', windows_fonts + 'ARIALUNI.TTF', uni=True)
            self.add_font('ArialUnicode', 'B', windows_fonts + 'ARIALUNI.TTF', uni=True)
        except:
            try:
                # Segoe UI - Windows default UI font, good Unicode support
                self.add_font('SegoeUI', '', windows_fonts + 'segoeui.ttf', uni=True)
                self.add_font('SegoeUI', 'B', windows_fonts + 'segoeuib.ttf', uni=True)
                self.add_font('SegoeUI', 'I', windows_fonts + 'segoeuii.ttf', uni=True)
            except:
                try:
                    # Tahoma - another good Unicode font
                    self.add_font('Tahoma', '', windows_fonts + 'tahoma.ttf', uni=True)
                    self.add_font('Tahoma', 'B', windows_fonts + 'tahomabd.ttf', uni=True)
                except:
                    # Fallback to Arial (limited Unicode support but works for basic chars)
                    pass
        
    def header(self):
        # Try to use Unicode font, fallback to Helvetica
        try:
            self.set_font('ArialUnicode', 'B', 12)
        except:
            try:
                self.set_font('SegoeUI', 'B', 12)
            except:
                try:
                    self.set_font('Tahoma', 'B', 12)
                except:
                    self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Portfolio Risk Analysis Report', 0, 0, 'L')
        
        self.set_font('Helvetica', '', 8)  # Date in simple font
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'R')
        self.ln(10)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('SegoeUI', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        
    def chapter_title(self, title: str):
        self.set_font('SegoeUI', 'B', 14)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, title, 0, 1, 'L', True)
        self.ln(5)
        
    def chapter_body(self, body: str):
        self.set_font('SegoeUI', '', 11)
        # Replace bullet points with hyphens
        body = body.replace('•', '-')
        self.multi_cell(w=0, h=6, txt=body) # type: ignore
        self.ln()
        
    def add_table(self, title: str, df: DataFrame, col_widths: list[float] | None = None):
        self.set_font('SegoeUI', 'B', 12)
        self.cell(0, 8, title, 0, 1)
        
        if col_widths is None:
            col_widths = [self.w * 0.2 for _ in range(len(df.columns))]
        
        self.set_font('SegoeUI', 'B', 9)
        for i, col in enumerate(df.columns):
            # Clean column names
            col = str(col).encode('ascii', 'ignore').decode('ascii')
            self.cell(col_widths[i], 7, str(col), 1, 0, 'C')
        self.ln()
        
        self.set_font('SegoeUI', '', 9)
        for _, row in df.iterrows():
            for i, col in enumerate(df.columns):
                value = row[col]
                if isinstance(value, (int, float)):
                    if 'value' in col.lower() or 'price' in col.lower():
                        self.cell(col_widths[i], 6, f'{value:,.0f} RUB', 1, 0, 'R')
                    elif '%' in col or 'return' in col.lower() or 'yield' in col.lower():
                        self.cell(col_widths[i], 6, f'{value:.2f}%', 1, 0, 'R')
                    elif 'return' in col.lower() and 'rub' in str(value).lower():
                        self.cell(col_widths[i], 6, f'{value:,.0f} RUB', 1, 0, 'R')
                    else:
                        self.cell(col_widths[i], 6, f'{value:,.2f}', 1, 0, 'R')
                else:                    
                    self.cell(col_widths[i], 6, value, 1, 0, 'L')
            self.ln()
        self.ln(10)
