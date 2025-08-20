import markdown
from xhtml2pdf import pisa
import os
import re
from crewai.tools import tool

@tool
def markdown_to_pdf(markdown_content: str, project_name: str) -> str:
    """
    Convert Markdown content to a cleaned PDF file named after the project_name.

    Args:
        markdown_content (str): Raw Markdown content as a string.
        project_name (str): Name to use for the output PDF file (without extension).

    Returns:
        str: Success or error message.
    """
    try:
        output_file_name = f"output/{project_name}.pdf"

      
        cleaned_content = re.sub(r"```[\w]*", "", markdown_content)
        cleaned_content = re.sub(r"```", "", cleaned_content)

       
        html_content = markdown.markdown(cleaned_content)

     
        with open(output_file_name, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

        if pisa_status.err:
            return f" Failed to convert Markdown content to {output_file_name}"
        else:
            return f" Successfully converted Markdown content to {output_file_name}"

    except Exception as e:
        return f" An error occurred: {e}"
