import os
import re
import markdown
from xhtml2pdf import pisa
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("markdown_tools")

@mcp.tool()
def markdown_to_pdf(markdown_content: str, project_name: str) -> str:
    """
    Convert Markdown content into a cleaned PDF file named after project_name.

    Args:
        markdown_content (str): Raw Markdown content as a string.
        project_name (str): Name to use for the output PDF file (without extension).

    Returns:
        str: Success or error message.
    """
    try:
        os.makedirs("output", exist_ok=True)
        output_file_name = f"output/{project_name}.pdf"

        # Clean fenced code blocks
        cleaned_content = re.sub(r"```[\w]*", "", markdown_content)
        cleaned_content = re.sub(r"```", "", cleaned_content)

        # Convert Markdown → HTML
        html_content = markdown.markdown(cleaned_content)

        # Write to PDF
        with open(output_file_name, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

        if pisa_status.err:
            return f" Failed to convert Markdown content to {output_file_name}"
        else:
            return f" Successfully converted Markdown content to {output_file_name}"

    except Exception as e:
        return f" An error occurred: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
