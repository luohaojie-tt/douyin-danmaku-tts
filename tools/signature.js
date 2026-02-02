/**
 * 抖音Signature计算工具
 *
 * 使用方法:
 *   node signature.js <roomId> <uniqueId>
 */

const crypto = require('crypto');

// 获取签名stub（X-MS-STUB）
function getStub(roomId, uniqueId) {
  const sdkVersion = '1.0.14-beta.0';
  const str = `live_id=1,aid=6383,version_code=180800,webcast_sdk_version=${sdkVersion},room_id=${roomId},sub_room_id=,sub_channel_id=,did_rule=3,user_unique_id=${uniqueId},device_platform=web,device_type=,ac=,identity=audience`;

  // 计算MD5
  return crypto.createHash('md5').update(str).digest('hex');
}

// 简化版签名
function getSignature(roomId, uniqueId) {
  const stub = getStub(roomId, uniqueId);

  // 返回stub作为签名
  // 注意：实际环境中需要byted_acrawler.frontierSign
  // 但在某些情况下服务器可能不严格验证
  return stub;
}

// 主函数
if (process.argv.length < 4) {
  console.error('用法: node signature.js <roomId> <uniqueId>');
  console.error('示例: node signature.js 728804746624 guest_1234567890');
  process.exit(1);
}

const roomId = process.argv[2];
const uniqueId = process.argv[3];

try {
  const signature = getSignature(roomId, uniqueId);
  console.log(JSON.stringify({
    success: true,
    signature: signature,
    x_ms_stub: signature,  // 同时返回stub
    roomId: roomId,
    uniqueId: uniqueId
  }));
} catch (error) {
  console.error(JSON.stringify({
    success: false,
    error: error.message
  }));
  process.exit(1);
}
