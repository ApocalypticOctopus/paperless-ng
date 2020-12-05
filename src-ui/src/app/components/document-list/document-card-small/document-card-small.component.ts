import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { fadeAnimation } from 'src/app/animations';
import { PaperlessDocument } from 'src/app/data/paperless-document';
import { PaperlessTag } from 'src/app/data/paperless-tag';
import { DocumentService } from 'src/app/services/rest/document.service';

@Component({
  selector: 'app-document-card-small',
  templateUrl: './document-card-small.component.html',
  styleUrls: ['./document-card-small.component.scss'],
  animations: [
    fadeAnimation
  ]
})
export class DocumentCardSmallComponent implements OnInit {

  constructor(private documentService: DocumentService) { }

  imageLoaded = false

  @Input()
  document: PaperlessDocument

  @Output()
  clickTag = new EventEmitter<number>()

  @Output()
  clickCorrespondent = new EventEmitter<number>()

  ngOnInit(): void {
  }

  getThumbUrl() {
    return this.documentService.getThumbUrl(this.document.id)
  }

  getDownloadUrl() {
    return this.documentService.getDownloadUrl(this.document.id)
  }

  getPreviewUrl() {
    return this.documentService.getPreviewUrl(this.document.id)
  }
}
