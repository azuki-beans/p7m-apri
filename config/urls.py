from django.urls import path

from converter import views as converter_views
from fatture import views as fatture_views

urlpatterns = [
    path("", converter_views.index, name="index"),
    path("verify/", converter_views.verify, name="verify"),
    path("download/<uuid:pk>/", converter_views.download, name="download"),
    # Visualizzatore di fatture elettroniche (XML/p7m -> PDF).
    path("fatture/", fatture_views.index, name="fatture"),
    path("fatture/render/", fatture_views.render_view, name="fattura_render"),
    path("fatture/pdf/<uuid:pk>/", fatture_views.pdf_view, name="fattura_pdf"),
    path("fatture/da-conversione/<uuid:pk>/",
         fatture_views.from_conversion, name="fattura_da_conversione"),
    # API: fattura XML o .p7m -> PDF.
    path("fatture/api/pdf/", fatture_views.api_pdf, name="api_fattura_pdf"),
]
