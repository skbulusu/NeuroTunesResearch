declare module 'aws-sdk' {
  export class S3 {
    constructor(options?: any);
    upload(params: any): { promise(): Promise<any> };
  }
}
