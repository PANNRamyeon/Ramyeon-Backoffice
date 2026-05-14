"""
POS Page API Views
Base URL: /api/v1/admin/pos-pages/

Endpoints:
  GET    /pos-pages/                        list all pages
  POST   /pos-pages/                        create a page
  GET    /pos-pages/<page_id>/              get a page
  PUT    /pos-pages/<page_id>/              rename / change icon
  DELETE /pos-pages/<page_id>/              delete a page
  POST   /pos-pages/<page_id>/products/     add products to page
  DELETE /pos-pages/<page_id>/products/     remove products from page
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from models.PosPage import PosPage
import logging

logger = logging.getLogger(__name__)


class PosPageListView(APIView):

    def get(self, request):
        try:
            pages = PosPage.get_all_pages()
            return Response({
                "pages": [p.to_dict() for p in pages],
                "count": len(pages),
            })
        except Exception as e:
            logger.error(f"Error listing pos pages: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        page_name = (request.data.get("page_name") or "").strip()
        icon = (request.data.get("icon") or "Package").strip()

        if not page_name:
            return Response({"error": "page_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            page = PosPage.create_page(page_name=page_name, icon=icon)
            return Response({"page": page.to_dict()}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating pos page: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PosPageDetailView(APIView):

    def _get_or_404(self, page_id):
        page = PosPage.get_page(page_id)
        if not page:
            return None, Response({"error": f"Page '{page_id}' not found"}, status=status.HTTP_404_NOT_FOUND)
        return page, None

    def get(self, request, page_id):
        page, err = self._get_or_404(page_id)
        if err:
            return err
        return Response({"page": page.to_dict()})

    def put(self, request, page_id):
        page, err = self._get_or_404(page_id)
        if err:
            return err

        try:
            if "page_name" in request.data:
                name = (request.data["page_name"] or "").strip()
                if not name:
                    return Response({"error": "page_name cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
                page.page_name = name
            if "icon" in request.data:
                page.icon = (request.data["icon"] or "Package").strip()
            if "product_ids" in request.data:
                ids = request.data.get("product_ids", [])
                if isinstance(ids, list):
                    page.product_ids = [str(p) for p in ids]

            from datetime import datetime
            page.updated_at = datetime.utcnow().isoformat()
            page.save()
            return Response({"page": page.to_dict()})
        except Exception as e:
            logger.error(f"Error updating pos page {page_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, page_id):
        page, err = self._get_or_404(page_id)
        if err:
            return err

        try:
            page.delete()
            return Response({"message": f"Page '{page_id}' deleted successfully"})
        except Exception as e:
            logger.error(f"Error deleting pos page {page_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PosPageProductsView(APIView):

    def _get_or_404(self, page_id):
        page = PosPage.get_page(page_id)
        if not page:
            return None, Response({"error": f"Page '{page_id}' not found"}, status=status.HTTP_404_NOT_FOUND)
        return page, None

    def post(self, request, page_id):
        """Add products to a page."""
        page, err = self._get_or_404(page_id)
        if err:
            return err

        product_ids = request.data.get("product_ids", [])
        if not isinstance(product_ids, list) or not product_ids:
            return Response({"error": "product_ids must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            page.add_products(product_ids)
            return Response({"page": page.to_dict()})
        except Exception as e:
            logger.error(f"Error adding products to page {page_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, page_id):
        """Remove products from a page."""
        page, err = self._get_or_404(page_id)
        if err:
            return err

        product_ids = request.data.get("product_ids", [])
        if not isinstance(product_ids, list) or not product_ids:
            return Response({"error": "product_ids must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            page.remove_products(product_ids)
            return Response({"page": page.to_dict()})
        except Exception as e:
            logger.error(f"Error removing products from page {page_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
