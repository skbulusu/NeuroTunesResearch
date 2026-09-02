// Type definitions for dropbox-v2-api
// File: types/dropbox-v2-api.d.ts

declare module 'dropbox-v2-api' {
  interface DropboxConfig {
    token: string;
  }

  interface DropboxUploadParams {
    resource: string;
    parameters: {
      path: string;
    };
    readStream: Buffer;
  }

  interface DropboxApi {
    (params: DropboxUploadParams, callback: (err: any, result: any) => void): void;
  }

  function authenticate(config: DropboxConfig): DropboxApi;

  export = { authenticate };
}
